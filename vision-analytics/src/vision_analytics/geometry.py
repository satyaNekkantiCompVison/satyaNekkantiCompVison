from __future__ import annotations


def side_of_line(
    point: tuple[float, float],
    line: tuple[tuple[float, float], tuple[float, float]],
) -> float:
    """Signed side of a directed line. Positive is to the left of A->B."""
    (x1, y1), (x2, y2) = line
    x, y = point
    return (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)


def crossed_line(
    prev: tuple[float, float],
    curr: tuple[float, float],
    line: tuple[tuple[float, float], tuple[float, float]],
) -> int:
    """Return +1 / -1 when the segment prev->curr crosses the line, else 0.

    Sign follows the directed line: +1 means crossed from right to left of A->B
    (i.e. signed side went negative -> positive).
    """
    s0 = side_of_line(prev, line)
    s1 = side_of_line(curr, line)
    if s0 == 0 or s1 == 0:
        return 0
    if (s0 > 0) == (s1 > 0):
        return 0
    # Also require the crossing to happen within the line segment extent.
    (x1, y1), (x2, y2) = line
    minx, maxx = min(x1, x2), max(x1, x2)
    miny, maxy = min(y1, y2), max(y1, y2)
    pad = max(12.0, 0.03 * max(maxx - minx, maxy - miny, 1.0))
    cx = (prev[0] + curr[0]) / 2.0
    cy = (prev[1] + curr[1]) / 2.0
    if not (minx - pad <= cx <= maxx + pad and miny - pad <= cy <= maxy + pad):
        return 0
    return 1 if s1 > 0 else -1


def denorm_line(
    line: list[list[float]],
    width: int,
    height: int,
) -> tuple[tuple[float, float], tuple[float, float]]:
    (x1, y1), (x2, y2) = line
    return ((x1 * width, y1 * height), (x2 * width, y2 * height))


def unit_vector(direction: str) -> tuple[float, float]:
    mapping = {
        "left_to_right": (1.0, 0.0),
        "right_to_left": (-1.0, 0.0),
        "top_to_bottom": (0.0, 1.0),
        "bottom_to_top": (0.0, -1.0),
        "right": (1.0, 0.0),
        "left": (-1.0, 0.0),
        "down": (0.0, 1.0),
        "up": (0.0, -1.0),
    }
    return mapping[direction]


def normalize_xyxy(xyxy: tuple[float, float, float, float], w: int, h: int) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = xyxy
    return (x1 / w, y1 / h, x2 / w, y2 / h)
