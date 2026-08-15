from __future__ import annotations

import time
from typing import Any

import numpy as np

from vision_analytics.config import StoreModuleConfig
from vision_analytics.geometry import crossed_line, denorm_line, unit_vector
from vision_analytics.tracking.iou_tracker import IOUTracker
from vision_analytics.types import Detection, Track


class StoreAnalyzer:
    """People counting (line crossing) and occupancy heat map."""

    def __init__(self, camera_id: str, cfg: StoreModuleConfig) -> None:
        self.camera_id = camera_id
        self.cfg = cfg
        self.tracker = IOUTracker()
        bins_w, bins_h = cfg.heatmap_bins
        self.heatmap = np.zeros((bins_h, bins_w), dtype=np.float32)
        self.in_count = 0
        self.out_count = 0
        self.occupancy = 0
        self._seen_cross: set[tuple[int, str]] = set()

    def update(
        self,
        detections: list[Detection],
        frame_wh: tuple[int, int],
        now: float | None = None,
    ) -> list[dict[str, Any]]:
        now = now if now is not None else time.time()
        people = [d for d in detections if d.label.lower() == "person"]
        tracks = self.tracker.update(people)
        live = [t for t in tracks if t.time_since_update == 0]
        self.occupancy = len(live)
        w, h = frame_wh
        self._accumulate_heatmap(live, w, h)
        events = self._count_crossings(live, w, h, now)
        return events

    def _accumulate_heatmap(self, tracks: list[Track], w: int, h: int) -> None:
        bins_h, bins_w = self.heatmap.shape
        for tr in tracks:
            fx, fy = tr.xyxy[0] * 0 + ((tr.xyxy[0] + tr.xyxy[2]) / 2.0), tr.xyxy[3]
            col = int(np.clip((fx / max(w, 1)) * bins_w, 0, bins_w - 1))
            row = int(np.clip((fy / max(h, 1)) * bins_h, 0, bins_h - 1))
            self.heatmap[row, col] += 1.0

    def _count_crossings(
        self, tracks: list[Track], w: int, h: int, now: float
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        line = denorm_line(self.cfg.count_line, w, h)
        desired = unit_vector(self.cfg.in_direction)
        for tr in tracks:
            if len(tr.history) < 2 or tr.hits < 2:
                continue
            key = (tr.track_id, "count")
            if key in self._seen_cross:
                continue
            direction = crossed_line(tr.history[-2], tr.history[-1], line)
            if direction == 0:
                continue
            vx, vy = tr.velocity
            inward = vx * desired[0] + vy * desired[1]
            self._seen_cross.add(key)
            if inward >= 0:
                self.in_count += 1
                kind = "enter"
            else:
                self.out_count += 1
                kind = "exit"
            events.append(
                {
                    "type": "people_count",
                    "camera_id": self.camera_id,
                    "kind": kind,
                    "track_id": tr.track_id,
                    "in_count": self.in_count,
                    "out_count": self.out_count,
                    "occupancy": self.occupancy,
                    "ts": now,
                }
            )
        return events

    def heatmap_normalized(self) -> list[list[float]]:
        peak = float(self.heatmap.max()) if self.heatmap.size else 0.0
        if peak <= 0:
            return self.heatmap.tolist()
        return (self.heatmap / peak).tolist()

    def snapshot(self) -> dict[str, Any]:
        return {
            "in_count": self.in_count,
            "out_count": self.out_count,
            "occupancy": self.occupancy,
            "net": self.in_count - self.out_count,
        }
