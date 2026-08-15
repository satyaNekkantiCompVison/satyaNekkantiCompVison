from __future__ import annotations

import time
from typing import Any

import numpy as np

from vision_analytics.config import TrafficModuleConfig
from vision_analytics.geometry import crossed_line, denorm_line, unit_vector
from vision_analytics.tracking.iou_tracker import IOUTracker
from vision_analytics.types import COCO_TRAFFIC_LIGHT, COCO_VEHICLES, Detection, Track

VEHICLE_LABELS = {"bicycle", "car", "motorcycle", "bus", "truck", "vehicle"}


def classify_signal_color(frame: np.ndarray, xyxy: tuple[float, float, float, float]) -> str:
    """Estimate red/yellow/green from the brightest channel in the light crop."""
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = xyxy
    x1i, y1i = max(0, int(x1)), max(0, int(y1))
    x2i, y2i = min(w, int(x2)), min(h, int(y2))
    if x2i <= x1i or y2i <= y1i:
        return "unknown"
    crop = frame[y1i:y2i, x1i:x2i]
    if crop.size == 0:
        return "unknown"
    # Split crop into 3 vertical bands (typical stacked signal).
    bands = np.array_split(crop, 3, axis=0)
    scores: list[tuple[str, float]] = []
    labels = ("red", "yellow", "green")
    for label, band in zip(labels, bands, strict=False):
        if band.size == 0:
            scores.append((label, 0.0))
            continue
        b, g, r = cv_mean_bgr(band)
        if label == "red":
            scores.append((label, r - max(g, b)))
        elif label == "yellow":
            scores.append((label, (r + g) / 2.0 - b))
        else:
            scores.append((label, g - max(r, b)))
    best_label, best_score = max(scores, key=lambda t: t[1])
    if best_score < 8:
        # Fallback: global mean color.
        b, g, r = cv_mean_bgr(crop)
        if r > g * 1.2 and r > b * 1.2:
            return "red"
        if g > r * 1.15 and g > b:
            return "green"
        if r > 80 and g > 80 and b < r * 0.85:
            return "yellow"
        return "unknown"
    return best_label


def cv_mean_bgr(img: np.ndarray) -> tuple[float, float, float]:
    means = img.reshape(-1, 3).mean(axis=0)
    return float(means[0]), float(means[1]), float(means[2])


class TrafficAnalyzer:
    """Wrong-way, signal jumping, and vehicles crossing the stop line."""

    def __init__(self, camera_id: str, cfg: TrafficModuleConfig) -> None:
        self.camera_id = camera_id
        self.cfg = cfg
        self.tracker = IOUTracker(iou_threshold=0.25, max_age=25)
        self.vehicles_crossed = 0
        self.wrong_way = 0
        self.signal_jumps = 0
        self.signal_color = "unknown"
        self._crossed: set[int] = set()
        self._wrong: set[int] = set()
        self._jumped: set[int] = set()

    def update(
        self,
        detections: list[Detection],
        frame: np.ndarray,
        now: float | None = None,
    ) -> list[dict[str, Any]]:
        now = now if now is not None else time.time()
        h, w = frame.shape[:2]
        vehicles = [
            d
            for d in detections
            if d.cls_id in COCO_VEHICLES or d.label.lower() in VEHICLE_LABELS
        ]
        lights = [
            d
            for d in detections
            if d.cls_id == COCO_TRAFFIC_LIGHT or d.label.lower() in {"traffic light", "traffic_light"}
        ]
        self.signal_color = self._read_signal(frame, lights, w, h)
        tracks = self.tracker.update(vehicles)
        live = [t for t in tracks if t.time_since_update == 0]
        events: list[dict[str, Any]] = []
        events.extend(self._wrong_way_events(live, now))
        events.extend(self._crossing_and_jump(live, w, h, now))
        return events

    def _read_signal(
        self,
        frame: np.ndarray,
        lights: list[Detection],
        w: int,
        h: int,
    ) -> str:
        if lights:
            best = max(lights, key=lambda d: d.conf)
            return classify_signal_color(frame, best.xyxy)
        sx1, sy1, sx2, sy2 = self.cfg.signal_roi
        crop_box = (sx1 * w, sy1 * h, sx2 * w, sy2 * h)
        return classify_signal_color(frame, crop_box)

    def _wrong_way_events(self, tracks: list[Track], now: float) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        allowed = unit_vector(self.cfg.allowed_direction)
        for tr in tracks:
            if tr.age < self.cfg.min_track_age or tr.track_id in self._wrong:
                continue
            vx, vy = tr.velocity
            speed = (vx * vx + vy * vy) ** 0.5
            if speed < 1.5:
                continue
            nx, ny = vx / speed, vy / speed
            dot = nx * allowed[0] + ny * allowed[1]
            if dot <= self.cfg.wrong_way_dot:
                self._wrong.add(tr.track_id)
                self.wrong_way += 1
                events.append(
                    {
                        "type": "wrong_way",
                        "severity": "high",
                        "camera_id": self.camera_id,
                        "track_id": tr.track_id,
                        "label": tr.label,
                        "dot": round(dot, 3),
                        "ts": now,
                    }
                )
        return events

    def _crossing_and_jump(
        self, tracks: list[Track], w: int, h: int, now: float
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        line = denorm_line(self.cfg.stop_line, w, h)
        for tr in tracks:
            if len(tr.history) < 2 or tr.track_id in self._crossed:
                continue
            if crossed_line(tr.history[-2], tr.history[-1], line) == 0:
                continue
            self._crossed.add(tr.track_id)
            self.vehicles_crossed += 1
            events.append(
                {
                    "type": "vehicle_crossing",
                    "camera_id": self.camera_id,
                    "track_id": tr.track_id,
                    "label": tr.label,
                    "total": self.vehicles_crossed,
                    "signal": self.signal_color,
                    "ts": now,
                }
            )
            if self.signal_color == "red" and tr.track_id not in self._jumped:
                self._jumped.add(tr.track_id)
                self.signal_jumps += 1
                events.append(
                    {
                        "type": "signal_jump",
                        "severity": "critical",
                        "camera_id": self.camera_id,
                        "track_id": tr.track_id,
                        "label": tr.label,
                        "signal": self.signal_color,
                        "ts": now,
                    }
                )
        return events

    def snapshot(self) -> dict[str, Any]:
        return {
            "vehicles_crossed": self.vehicles_crossed,
            "wrong_way": self.wrong_way,
            "signal_jumps": self.signal_jumps,
            "signal_color": self.signal_color,
            "active_tracks": sum(1 for t in self.tracker.tracks.values() if t.time_since_update == 0),
        }
