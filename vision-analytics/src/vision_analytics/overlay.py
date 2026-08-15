from __future__ import annotations

import cv2
import numpy as np

from vision_analytics.config import CameraConfig
from vision_analytics.types import Detection, Track


def draw_overlay(
    frame: np.ndarray,
    camera: CameraConfig,
    detections: list[Detection],
    tracks: list[Track] | None = None,
    signal_color: str | None = None,
    occupancy: int | None = None,
) -> np.ndarray:
    vis = frame.copy()
    h, w = vis.shape[:2]
    color_map = {
        "person": (80, 180, 255),
        "car": (40, 90, 220),
        "truck": (40, 90, 220),
        "bus": (40, 90, 220),
        "motorcycle": (40, 90, 220),
        "bicycle": (40, 90, 220),
        "fire": (0, 0, 255),
        "smoke": (200, 200, 200),
        "traffic light": (0, 255, 255),
    }
    for det in detections:
        x1, y1, x2, y2 = map(int, det.xyxy)
        color = color_map.get(det.label.lower(), (0, 220, 0))
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            vis,
            f"{det.label} {det.conf:.2f}",
            (x1, max(16, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA,
        )
    if tracks:
        for tr in tracks:
            if tr.time_since_update:
                continue
            cx, cy = map(int, tr.centroid)
            cv2.putText(vis, f"id {tr.track_id}", (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

    if "store" in camera.modules:
        (x1, y1), (x2, y2) = camera.store.count_line
        cv2.line(vis, (int(x1 * w), int(y1 * h)), (int(x2 * w), int(y2 * h)), (0, 200, 255), 2)
        if occupancy is not None:
            cv2.putText(vis, f"occ {occupancy}", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
    if "traffic" in camera.modules:
        (x1, y1), (x2, y2) = camera.traffic.stop_line
        cv2.line(vis, (int(x1 * w), int(y1 * h)), (int(x2 * w), int(y2 * h)), (255, 255, 255), 2)
        sx1, sy1, sx2, sy2 = camera.traffic.signal_roi
        cv2.rectangle(vis, (int(sx1 * w), int(sy1 * h)), (int(sx2 * w), int(sy2 * h)), (0, 255, 255), 1)
        if signal_color:
            cv2.putText(vis, f"signal {signal_color}", (12, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(vis, camera.name, (12, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)
    return vis


def heatmap_image(grid: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    peak = float(grid.max()) if grid.size else 0.0
    norm = (grid / peak * 255).astype(np.uint8) if peak > 0 else grid.astype(np.uint8)
    color = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
    return cv2.resize(color, size, interpolation=cv2.INTER_LINEAR)
