from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any


class ThroughputMeter:
    """Rolling FPS / latency meter for the shared GPU worker."""

    def __init__(self, window_sec: float = 5.0) -> None:
        self.window_sec = window_sec
        self._lock = threading.Lock()
        self._events: deque[tuple[float, int, float]] = deque()
        self.batches = 0
        self.frames = 0

    def record(self, n_frames: int, latency_s: float) -> None:
        now = time.monotonic()
        with self._lock:
            self._events.append((now, n_frames, latency_s))
            self.batches += 1
            self.frames += n_frames
            self._trim(now)

    def _trim(self, now: float) -> None:
        cutoff = now - self.window_sec
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()

    def snapshot(self) -> dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            self._trim(now)
            frames = sum(e[1] for e in self._events)
            lat = [e[2] for e in self._events]
            span = self.window_sec
            if self._events:
                span = max(now - self._events[0][0], 1e-6)
            avg_lat = sum(lat) / len(lat) if lat else 0.0
            avg_batch = frames / len(self._events) if self._events else 0.0
            return {
                "fps": frames / span,
                "avg_batch_size": avg_batch,
                "avg_latency_ms": avg_lat * 1000.0,
                "window_frames": frames,
                "total_frames": self.frames,
                "total_batches": self.batches,
            }
