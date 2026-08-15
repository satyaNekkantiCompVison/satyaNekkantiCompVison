from __future__ import annotations

import numpy as np

from vision_analytics.geometry import crossed_line, side_of_line, unit_vector


def test_horizontal_line_downward_cross():
    line = ((100.0, 200.0), (400.0, 200.0))
    assert side_of_line((250.0, 100.0), line) > 0
    assert side_of_line((250.0, 300.0), line) < 0
    assert crossed_line((250.0, 100.0), (250.0, 300.0), line) == -1
    assert crossed_line((250.0, 300.0), (250.0, 100.0), line) == 1


def test_no_cross_when_parallel():
    line = ((100.0, 200.0), (400.0, 200.0))
    assert crossed_line((120.0, 100.0), (300.0, 100.0), line) == 0


def test_unit_vectors():
    assert unit_vector("left_to_right") == (1.0, 0.0)
    assert unit_vector("down") == (0.0, 1.0)
