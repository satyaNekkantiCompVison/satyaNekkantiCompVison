from __future__ import annotations

from vision_analytics.types import Detection, Track


def iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def centroid_affinity(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    """IOU plus a distance score so fast-moving boxes still match."""
    overlap = iou(a, b)
    if overlap > 0:
        return overlap
    ax = (a[0] + a[2]) / 2.0
    ay = (a[1] + a[3]) / 2.0
    bx = (b[0] + b[2]) / 2.0
    by = (b[1] + b[3]) / 2.0
    aw, ah = max(a[2] - a[0], 1.0), max(a[3] - a[1], 1.0)
    dist = ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
    gate = 4.0 * max(aw, ah)
    if dist > gate:
        return 0.0
    return max(0.0, 1.0 - dist / gate) * 0.49  # below typical IOU, used as fallback


class IOUTracker:
    """Lightweight IOU tracker shared by store and traffic modules."""

    def __init__(self, iou_threshold: float = 0.3, max_age: int = 20, max_history: int = 30) -> None:
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.max_history = max_history
        self.tracks: dict[int, Track] = {}
        self._next_id = 1

    def update(self, detections: list[Detection]) -> list[Track]:
        for t in self.tracks.values():
            t.time_since_update += 1

        unmatched = set(range(len(detections)))
        pairs: list[tuple[float, int, int]] = []
        track_ids = list(self.tracks.keys())
        for ti, tid in enumerate(track_ids):
            track = self.tracks[tid]
            for di, det in enumerate(detections):
                if det.label != track.label and det.cls_id != track.cls_id:
                    continue
                score = centroid_affinity(track.xyxy, det.xyxy)
                if score >= min(self.iou_threshold, 0.12):
                    pairs.append((score, ti, di))
        pairs.sort(reverse=True)
        used_tracks: set[int] = set()
        for score, ti, di in pairs:
            if ti in used_tracks or di not in unmatched:
                continue
            used_tracks.add(ti)
            unmatched.discard(di)
            self._touch(track_ids[ti], detections[di])

        for di in unmatched:
            self._spawn(detections[di])

        dead = [tid for tid, tr in self.tracks.items() if tr.time_since_update > self.max_age]
        for tid in dead:
            del self.tracks[tid]
        return list(self.tracks.values())

    def _touch(self, tid: int, det: Detection) -> None:
        tr = self.tracks[tid]
        tr.xyxy = det.xyxy
        tr.conf = det.conf
        tr.cls_id = det.cls_id
        tr.label = det.label
        tr.centroid = det.centroid
        tr.history.append(det.centroid)
        if len(tr.history) > self.max_history:
            tr.history = tr.history[-self.max_history :]
        tr.age += 1
        tr.hits += 1
        tr.time_since_update = 0

    def _spawn(self, det: Detection) -> None:
        tid = self._next_id
        self._next_id += 1
        self.tracks[tid] = Track(
            track_id=tid,
            xyxy=det.xyxy,
            conf=det.conf,
            cls_id=det.cls_id,
            label=det.label,
            centroid=det.centroid,
            history=[det.centroid],
            age=1,
            hits=1,
            time_since_update=0,
        )
