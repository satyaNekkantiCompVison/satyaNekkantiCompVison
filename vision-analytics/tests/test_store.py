from __future__ import annotations

from vision_analytics.analytics.store import StoreAnalyzer
from vision_analytics.config import StoreModuleConfig
from vision_analytics.types import Detection


def _person(x1, y1, x2, y2) -> Detection:
    return Detection(xyxy=(x1, y1, x2, y2), conf=0.9, cls_id=0, label="person")


def test_people_count_enter_and_exit():
    cfg = StoreModuleConfig(
        count_line=[[0.1, 0.5], [0.9, 0.5]],
        in_direction="down",
        heatmap_bins=[8, 8],
    )
    an = StoreAnalyzer("cam", cfg)
    w, h = 200, 200

    # Walk down across the mid line.
    an.update([_person(90, 40, 110, 80)], (w, h), now=1)
    ev = an.update([_person(90, 120, 110, 160)], (w, h), now=2)
    kinds = [e["kind"] for e in ev]
    assert "enter" in kinds
    assert an.in_count == 1

    # New person walking up (out).
    an2 = StoreAnalyzer("cam", cfg)
    an2.update([_person(90, 120, 110, 160)], (w, h), now=1)
    ev2 = an2.update([_person(90, 40, 110, 80)], (w, h), now=2)
    assert any(e["kind"] == "exit" for e in ev2)
    assert an2.out_count == 1


def test_heatmap_accumulates():
    cfg = StoreModuleConfig(heatmap_bins=[10, 10])
    an = StoreAnalyzer("cam", cfg)
    an.update([_person(0, 0, 20, 20)], (100, 100), now=1)
    assert float(an.heatmap.sum()) >= 1.0
    grid = an.heatmap_normalized()
    assert max(max(row) for row in grid) > 0
