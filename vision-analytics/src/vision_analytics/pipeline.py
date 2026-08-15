from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from vision_analytics.analytics.fire_smoke import FireSmokeAnalyzer
from vision_analytics.analytics.store import StoreAnalyzer
from vision_analytics.analytics.traffic import TrafficAnalyzer
from vision_analytics.config import AppConfig, CameraConfig
from vision_analytics.inference.models import Detector, load_detector, resolve_device
from vision_analytics.inference.pool import SharedInferenceEngine
from vision_analytics.ingest.rtsp import FrameSource, SyntheticSource
from vision_analytics.overlay import draw_overlay, heatmap_image
from vision_analytics.storage import EventStore
from vision_analytics.types import Detection, FIRE_CLASS_ALIASES

log = logging.getLogger(__name__)

COCO_FILTER = {
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "bus",
    "truck",
    "traffic light",
}


class CameraRuntime:
    def __init__(self, cfg: CameraConfig) -> None:
        self.cfg = cfg
        self.source: FrameSource
        if cfg.source.startswith("synthetic://"):
            mode = cfg.source.split("://", 1)[-1]
            self.source = SyntheticSource(cfg.id, mode=mode, sample_fps=cfg.sample_fps)
        else:
            self.source = FrameSource(cfg.id, cfg.source, cfg.sample_fps)
        self.store = StoreAnalyzer(cfg.id, cfg.store) if "store" in cfg.modules else None
        self.traffic = TrafficAnalyzer(cfg.id, cfg.traffic) if "traffic" in cfg.modules else None
        self.fire = FireSmokeAnalyzer(cfg.id, cfg.fire) if "fire" in cfg.modules else None
        self.last_frame: np.ndarray | None = None
        self.last_overlay: np.ndarray | None = None
        self.last_detections: list[Detection] = []
        self.last_ts = 0.0
        self.processed = 0


class AnalyticsPipeline:
    """Fan-in many cameras onto shared YOLO models, then fan-out analytics."""

    def __init__(self, config: AppConfig, mock: bool = False) -> None:
        self.config = config
        self.mock = mock
        self.device = resolve_device(config.engine.device)
        self.store = EventStore(config.storage.sqlite_path)
        Path(config.storage.snapshot_dir).mkdir(parents=True, exist_ok=True)
        self.models: dict[str, Detector] = {}
        self.engine: SharedInferenceEngine | None = None
        self.cameras: dict[str, CameraRuntime] = {}
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self.subscribers: list[Any] = []
        self._sub_lock = threading.Lock()

    def start(self) -> None:
        self._load_models()
        self.engine = SharedInferenceEngine(self.models, self.config.engine)
        self.engine.start()
        for cam in self.config.cameras:
            if not cam.enabled:
                continue
            rt = CameraRuntime(cam)
            rt.source.start()
            self.cameras[cam.id] = rt
            t = threading.Thread(target=self._camera_loop, args=(rt,), name=f"cam-{cam.id}", daemon=True)
            t.start()
            self._threads.append(t)
        log.info("pipeline started cameras=%s device=%s models=%s", list(self.cameras), self.device, list(self.models))

    def stop(self) -> None:
        self._stop.set()
        for rt in self.cameras.values():
            rt.source.stop()
        if self.engine:
            self.engine.stop()

    def subscribe(self, callback: Any) -> None:
        with self._sub_lock:
            self.subscribers.append(callback)

    def _emit(self, event: dict[str, Any]) -> None:
        stored = self.store.add(event)
        with self._sub_lock:
            subs = list(self.subscribers)
        for cb in subs:
            try:
                cb(stored)
            except Exception:
                log.exception("subscriber failed")

    def _load_models(self) -> None:
        needed = set()
        for cam in self.config.cameras:
            if not cam.enabled:
                continue
            if "store" in cam.modules or "traffic" in cam.modules:
                needed.add("coco")
            if "fire" in cam.modules:
                needed.add("fire")
        if not needed:
            needed.add("coco")

        for key in needed:
            slot = self.config.models.get(key)
            weights = slot.weights if slot else "yolov8n.pt"
            names_override = None
            class_filter = COCO_FILTER if key == "coco" else None
            if key == "fire" and slot and slot.classes:
                # Dedicated fire checkpoints often use 0=fire, 1=smoke
                names_override = {i: n for i, n in enumerate(slot.classes)}
                class_filter = set(slot.classes)
            try:
                self.models[key] = load_detector(
                    weights=weights,
                    device=self.device,
                    half=self.config.engine.half and self.device != "cpu",
                    class_filter=class_filter,
                    names_override=names_override,
                    mock=self.mock,
                )
            except Exception:
                log.exception("failed to load model %s from %s; using mock", key, weights)
                self.models[key] = load_detector(weights, self.device, False, mock=True)

        # If fire weights are actually a COCO checkpoint, keep the slot anyway;
        # demo/synthetic sources can still inject fire-like detections.
        if "fire" in self.models and "coco" not in self.models:
            self.models["coco"] = self.models["fire"]

    def _camera_loop(self, rt: CameraRuntime) -> None:
        last_seq = -1
        while not self._stop.is_set():
            packed = rt.source.buffer.get()
            if packed is None:
                time.sleep(0.01)
                continue
            seq, ts, frame = packed
            if seq == last_seq:
                time.sleep(0.005)
                continue
            last_seq = seq
            self._process_frame(rt, frame, ts)

    def _process_frame(self, rt: CameraRuntime, frame: np.ndarray, ts: float) -> None:
        assert self.engine is not None
        futures = []
        modules = set(rt.cfg.modules)
        if modules & {"store", "traffic"}:
            futures.append(("coco", self.engine.submit(rt.cfg.id, "coco", frame)))
        if "fire" in modules and "fire" in self.models:
            futures.append(("fire", self.engine.submit(rt.cfg.id, "fire", frame)))

        dets: list[Detection] = []
        for key, fut in futures:
            try:
                part = fut.result(timeout=2.0)
            except Exception:
                log.exception("inference failed camera=%s model=%s", rt.cfg.id, key)
                part = []
            if key == "fire":
                for d in part:
                    d.label = FIRE_CLASS_ALIASES.get(d.label.lower(), d.label)
            dets.extend(part)

        if rt.cfg.source.startswith("synthetic://fire") and not any(d.label.lower() in {"fire", "smoke"} for d in dets):
            dets.extend(_synthetic_fire_dets(frame, rt.cfg.id))

        events: list[dict[str, Any]] = []
        tracks = []
        occupancy = None
        signal = None
        h, w = frame.shape[:2]
        if rt.store:
            events.extend(rt.store.update(dets, (w, h), now=ts))
            tracks.extend([t for t in rt.store.tracker.tracks.values()])
            occupancy = rt.store.occupancy
        if rt.traffic:
            events.extend(rt.traffic.update(dets, frame, now=ts))
            tracks.extend([t for t in rt.traffic.tracker.tracks.values()])
            signal = rt.traffic.signal_color
        if rt.fire:
            events.extend(rt.fire.update(dets, now=ts))

        overlay = draw_overlay(frame, rt.cfg, dets, tracks, signal, occupancy)
        rt.last_frame = frame
        rt.last_overlay = overlay
        rt.last_detections = dets
        rt.last_ts = ts
        rt.processed += 1
        for ev in events:
            self._emit(ev)

    def camera_status(self) -> list[dict[str, Any]]:
        rows = []
        for rt in self.cameras.values():
            row: dict[str, Any] = {
                "id": rt.cfg.id,
                "name": rt.cfg.name,
                "modules": rt.cfg.modules,
                "source": rt.cfg.source,
                "alive": rt.source.alive,
                "error": rt.source.error,
                "decoded_fps": round(rt.source.decoded_fps, 2),
                "processed": rt.processed,
            }
            if rt.store:
                row["store"] = rt.store.snapshot()
            if rt.traffic:
                row["traffic"] = rt.traffic.snapshot()
            if rt.fire:
                row["fire"] = rt.fire.snapshot()
            rows.append(row)
        return rows

    def overlay_jpeg(self, camera_id: str, quality: int = 70) -> bytes | None:
        rt = self.cameras.get(camera_id)
        if not rt or rt.last_overlay is None:
            return None
        ok, buf = cv2.imencode(".jpg", rt.last_overlay, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        return buf.tobytes() if ok else None

    def heatmap_jpeg(self, camera_id: str) -> bytes | None:
        rt = self.cameras.get(camera_id)
        if not rt or not rt.store or rt.last_frame is None:
            return None
        h, w = rt.last_frame.shape[:2]
        img = heatmap_image(rt.store.heatmap, (w, h))
        blended = cv2.addWeighted(rt.last_frame, 0.45, img, 0.55, 0)
        ok, buf = cv2.imencode(".jpg", blended, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        return buf.tobytes() if ok else None

    def engine_stats(self) -> dict[str, Any]:
        if not self.engine:
            return {}
        stats = self.engine.stats()
        stats["device"] = self.device
        stats["cameras"] = len(self.cameras)
        return stats


def _synthetic_fire_dets(frame: np.ndarray, camera_id: str) -> list[Detection]:
    """When a dedicated fire checkpoint is not loaded, still demo the module on synthetic fire."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (0, 120, 120), (25, 255, 255))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    dets: list[Detection] = []
    for c in contours:
        if cv2.contourArea(c) < 400:
            continue
        x, y, bw, bh = cv2.boundingRect(c)
        dets.append(
            Detection(xyxy=(float(x), float(y), float(x + bw), float(y + bh)), conf=0.7, cls_id=80, label="fire", camera_id=camera_id)
        )
    return dets
