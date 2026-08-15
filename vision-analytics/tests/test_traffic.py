from __future__ import annotations

import numpy as np

from vision_analytics.analytics.traffic import TrafficAnalyzer, classify_signal_color
from vision_analytics.config import TrafficModuleConfig
from vision_analytics.types import Detection


def _car(x1, y1, x2, y2) -> Detection:
    return Detection(xyxy=(x1, y1, x2, y2), conf=0.9, cls_id=2, label="car")


def _frame(w=400, h=300, light="red") -> np.ndarray:
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = (40, 40, 40)
    # stacked signal in default ROI [0.7, 0.05, 0.9, 0.25]
    x1, y1, x2, y2 = int(0.7 * w), int(0.05 * h), int(0.9 * w), int(0.25 * h)
    img[y1:y2, x1:x2] = (15, 15, 15)
    band = (y2 - y1) // 3
    if light == "red":
        img[y1 : y1 + band, x1:x2] = (0, 0, 220)
    elif light == "green":
        img[y1 + 2 * band : y2, x1:x2] = (0, 200, 0)
    else:
        img[y1 + band : y1 + 2 * band, x1:x2] = (0, 200, 220)
    return img


def test_classify_signal_color():
    red = _frame(light="red")
    assert classify_signal_color(red, (0.7 * 400, 0.05 * 300, 0.9 * 400, 0.25 * 300)) == "red"
    green = _frame(light="green")
    assert classify_signal_color(green, (0.7 * 400, 0.05 * 300, 0.9 * 400, 0.25 * 300)) == "green"


def test_vehicle_crossing_and_signal_jump():
    cfg = TrafficModuleConfig(
        allowed_direction="left_to_right",
        stop_line=[[0.1, 0.7], [0.9, 0.7]],
        min_track_age=1,
    )
    an = TrafficAnalyzer("j1", cfg)
    frame = _frame(light="red")
    w, h = 400, 300
    # car above then below stop line (y=0.7*300=210)
    an.update([_car(180, 150, 220, 190)], frame, now=1)
    events = an.update([_car(180, 220, 220, 260)], frame, now=2)
    types = [e["type"] for e in events]
    assert "vehicle_crossing" in types
    assert "signal_jump" in types
    assert an.vehicles_crossed == 1
    assert an.signal_jumps == 1


def test_wrong_way():
    cfg = TrafficModuleConfig(
        allowed_direction="left_to_right",
        stop_line=[[0.1, 0.9], [0.9, 0.9]],
        min_track_age=3,
        wrong_way_dot=-0.2,
    )
    an = TrafficAnalyzer("j1", cfg)
    frame = _frame(light="green")
    # Move clearly right-to-left over several frames.
    xs = [350, 300, 250, 200, 150]
    events = []
    for i, x in enumerate(xs):
        events.extend(an.update([_car(x, 140, x + 40, 180)], frame, now=i))
    assert any(e["type"] == "wrong_way" for e in events)
    assert an.wrong_way >= 1
