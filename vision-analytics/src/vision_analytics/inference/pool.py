from __future__ import annotations

import queue
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass
from typing import Any

import numpy as np

from vision_analytics.config import EngineConfig
from vision_analytics.inference.models import Detector
from vision_analytics.metrics import ThroughputMeter
from vision_analytics.types import Detection


@dataclass
class _Job:
    camera_id: str
    model_key: str
    image: np.ndarray
    future: Future[list[Detection]]
    submitted_at: float


class SharedInferenceEngine:
    """One (or few) pretrained YOLO models shared across many RTSP cameras.

    Cameras enqueue frames; a single GPU worker dynamically batches them so
    aggregate throughput can approach the configured target (default 90 FPS)
    instead of running a separate model replica per stream.
    """

    def __init__(
        self,
        models: dict[str, Detector],
        engine: EngineConfig,
    ) -> None:
        self.models = models
        self.engine = engine
        self.meter = ThroughputMeter()
        self._queue: queue.Queue[_Job | None] = queue.Queue(maxsize=engine.max_batch_size * 32)
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self.dropped = 0
        self.submitted = 0
        self._lock = threading.Lock()

    def start(self) -> None:
        for i in range(max(1, self.engine.workers)):
            t = threading.Thread(target=self._worker, name=f"gpu-worker-{i}", daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self) -> None:
        self._stop.set()
        for _ in self._threads:
            try:
                self._queue.put_nowait(None)
            except queue.Full:
                pass
        for t in self._threads:
            t.join(timeout=2.0)

    def submit(self, camera_id: str, model_key: str, image: np.ndarray) -> Future[list[Detection]]:
        fut: Future[list[Detection]] = Future()
        job = _Job(camera_id, model_key, image, fut, time.monotonic())
        try:
            self._queue.put_nowait(job)
            with self._lock:
                self.submitted += 1
        except queue.Full:
            with self._lock:
                self.dropped += 1
            fut.set_result([])
        return fut

    def stats(self) -> dict[str, Any]:
        snap = self.meter.snapshot()
        with self._lock:
            snap["submitted"] = self.submitted
            snap["dropped"] = self.dropped
            snap["queue_depth"] = self._queue.qsize()
            snap["target_fps"] = self.engine.target_fps
            snap["max_batch_size"] = self.engine.max_batch_size
            snap["models"] = list(self.models.keys())
            snap["meeting_target"] = snap["fps"] >= self.engine.target_fps * 0.85
        return snap

    def _worker(self) -> None:
        wait_s = self.engine.max_batch_wait_ms / 1000.0
        while not self._stop.is_set():
            batch = self._collect_batch(wait_s)
            if not batch:
                continue
            grouped: dict[str, list[_Job]] = {}
            for job in batch:
                grouped.setdefault(job.model_key, []).append(job)
            for model_key, jobs in grouped.items():
                self._infer_group(model_key, jobs)

    def _collect_batch(self, wait_s: float) -> list[_Job]:
        batch: list[_Job] = []
        try:
            first = self._queue.get(timeout=0.05)
        except queue.Empty:
            return batch
        if first is None:
            return batch
        batch.append(first)
        deadline = time.monotonic() + wait_s
        while len(batch) < self.engine.max_batch_size:
            timeout = deadline - time.monotonic()
            if timeout <= 0:
                break
            try:
                item = self._queue.get(timeout=timeout)
            except queue.Empty:
                break
            if item is None:
                break
            batch.append(item)
        return batch

    def _infer_group(self, model_key: str, jobs: list[_Job]) -> None:
        detector = self.models.get(model_key)
        if detector is None:
            for job in jobs:
                if not job.future.done():
                    job.future.set_result([])
            return
        images = [j.image for j in jobs]
        t0 = time.perf_counter()
        try:
            outputs = detector.predict_batch(
                images,
                conf=self.engine.conf,
                iou=self.engine.iou,
                imgsz=self.engine.imgsz,
            )
        except Exception as exc:
            for job in jobs:
                if not job.future.done():
                    job.future.set_exception(exc)
            return
        latency = time.perf_counter() - t0
        self.meter.record(len(jobs), latency)
        if len(outputs) < len(jobs):
            outputs = list(outputs) + [[] for _ in range(len(jobs) - len(outputs))]
        for job, dets in zip(jobs, outputs, strict=False):
            for d in dets:
                d.camera_id = job.camera_id
            if not job.future.done():
                job.future.set_result(dets)
