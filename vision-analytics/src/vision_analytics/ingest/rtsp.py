from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable

import cv2
import numpy as np


class LatestFrameBuffer:
    """Keep only the newest frame so slow inference never builds RTSP lag."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.frame: np.ndarray | None = None
        self.seq = 0
        self.timestamp = 0.0

    def put(self, frame: np.ndarray) -> None:
        with self._lock:
            self.frame = frame
            self.seq += 1
            self.timestamp = time.time()

    def get(self) -> tuple[int, float, np.ndarray] | None:
        with self._lock:
            if self.frame is None:
                return None
            return self.seq, self.timestamp, self.frame.copy()


class FrameSource:
    def __init__(self, camera_id: str, source: str, sample_fps: float) -> None:
        self.camera_id = camera_id
        self.source = source
        self.sample_fps = max(sample_fps, 0.5)
        self.buffer = LatestFrameBuffer()
        self.alive = False
        self.error: str | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.decoded_fps = 0.0
        self._decoded = deque(maxlen=60)

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name=f"ingest-{self.camera_id}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _open_capture(self) -> cv2.VideoCapture:
        src: str | int = self.source
        if self.source.isdigit():
            src = int(self.source)
        cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG if isinstance(src, str) and src.startswith("rtsp") else cv2.CAP_ANY)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def _loop(self) -> None:
        min_interval = 1.0 / self.sample_fps
        last_emit = 0.0
        while not self._stop.is_set():
            cap = self._open_capture()
            if not cap.isOpened():
                self.alive = False
                self.error = f"unable to open source {self.source}"
                time.sleep(2.0)
                continue
            self.alive = True
            self.error = None
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    self.alive = False
                    self.error = "frame read failed (reconnect)"
                    break
                now = time.monotonic()
                self._decoded.append(now)
                if len(self._decoded) >= 2:
                    span = self._decoded[-1] - self._decoded[0]
                    self.decoded_fps = (len(self._decoded) - 1) / max(span, 1e-6)
                if now - last_emit < min_interval:
                    continue
                last_emit = now
                self.buffer.put(frame)
            cap.release()
            time.sleep(0.5)


class SyntheticSource(FrameSource):
    """Procedural scene used for demo / tests when no RTSP camera is available."""

    def __init__(
        self,
        camera_id: str,
        mode: str = "store",
        sample_fps: float = 15.0,
        size: tuple[int, int] = (960, 540),
    ) -> None:
        super().__init__(camera_id, source=f"synthetic://{mode}", sample_fps=sample_fps)
        self.mode = mode
        self.size = size
        self.tick = 0
        self._generator: Callable[[int], np.ndarray] = {
            "store": self._store_frame,
            "traffic": self._traffic_frame,
            "fire": self._fire_frame,
        }.get(mode, self._store_frame)

    def _loop(self) -> None:
        self.alive = True
        interval = 1.0 / self.sample_fps
        while not self._stop.is_set():
            frame = self._generator(self.tick)
            self.tick += 1
            self.buffer.put(frame)
            self.decoded_fps = self.sample_fps
            time.sleep(interval)

    def _blank(self, color: tuple[int, int, int]) -> np.ndarray:
        w, h = self.size
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = color
        return img

    def _store_frame(self, tick: int) -> np.ndarray:
        img = self._blank((40, 40, 40))
        h, w = img.shape[:2]
        cv2.line(img, (int(0.15 * w), int(0.72 * h)), (int(0.85 * w), int(0.72 * h)), (0, 200, 255), 2)
        # Person walking down then up.
        cycle = tick % 80
        if cycle < 40:
            y = int(0.2 * h + (cycle / 40) * 0.7 * h)
        else:
            y = int(0.9 * h - ((cycle - 40) / 40) * 0.7 * h)
        x = int(0.5 * w)
        cv2.rectangle(img, (x - 18, y - 50), (x + 18, y), (80, 180, 255), -1)
        cv2.circle(img, (x, y - 62), 12, (80, 180, 255), -1)
        return img

    def _traffic_frame(self, tick: int) -> np.ndarray:
        img = self._blank((35, 35, 35))
        h, w = img.shape[:2]
        cv2.line(img, (int(0.1 * w), int(0.78 * h)), (int(0.9 * w), int(0.78 * h)), (255, 255, 255), 2)
        # Traffic light in ROI.
        lx1, ly1, lx2, ly2 = int(0.62 * w), int(0.08 * h), int(0.78 * w), int(0.28 * h)
        cv2.rectangle(img, (lx1, ly1), (lx2, ly2), (20, 20, 20), -1)
        phase = (tick // 50) % 3
        colors = [(0, 0, 220), (0, 200, 220), (0, 200, 0)]  # red, yellow, green BGR
        band_h = (ly2 - ly1) // 3
        for i, col in enumerate(colors):
            cy = ly1 + band_h * i + band_h // 2
            fill = col if i == phase else (40, 40, 40)
            cv2.circle(img, ((lx1 + lx2) // 2, cy), 12, fill, -1)
        # Vehicle: mostly L->R; every 3rd vehicle goes the wrong way.
        trip = tick % 90
        wrong = (tick // 90) % 3 == 2
        if wrong:
            x = int(0.95 * w - (trip / 90) * 1.1 * w)
        else:
            x = int(-0.1 * w + (trip / 90) * 1.2 * w)
        y = int(0.70 * h)
        cv2.rectangle(img, (x - 40, y - 22), (x + 40, y + 18), (40, 90, 220), -1)
        return img

    def _fire_frame(self, tick: int) -> np.ndarray:
        img = self._blank((30, 30, 30))
        h, w = img.shape[:2]
        if tick % 80 > 20:
            cx, cy = int(0.4 * w), int(0.55 * h)
            cv2.ellipse(img, (cx, cy), (40, 70), 0, 0, 360, (0, 60, 240), -1)
            cv2.ellipse(img, (cx, cy - 30), (22, 40), 0, 0, 360, (0, 160, 255), -1)
            cv2.ellipse(img, (cx + 80, cy - 10), (50, 30), 0, 0, 360, (180, 180, 180), -1)
        return img
