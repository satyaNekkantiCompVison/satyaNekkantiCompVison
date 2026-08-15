from __future__ import annotations

from dataclasses import dataclass, field


COCO_PERSON = 0
COCO_VEHICLES = {1, 2, 3, 5, 7}  # bicycle, car, motorcycle, bus, truck
COCO_TRAFFIC_LIGHT = 9

FIRE_CLASS_ALIASES = {
    "fire": "fire",
    "flame": "fire",
    "smoke": "smoke",
}


@dataclass
class Detection:
    xyxy: tuple[float, float, float, float]
    conf: float
    cls_id: int
    label: str
    camera_id: str = ""

    @property
    def centroid(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.xyxy
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @property
    def foot(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.xyxy
        return ((x1 + x2) / 2.0, y2)


@dataclass
class Track:
    track_id: int
    xyxy: tuple[float, float, float, float]
    conf: float
    cls_id: int
    label: str
    centroid: tuple[float, float]
    history: list[tuple[float, float]] = field(default_factory=list)
    age: int = 0
    hits: int = 0
    time_since_update: int = 0
    crossed: set[str] = field(default_factory=set)

    @property
    def velocity(self) -> tuple[float, float]:
        if len(self.history) < 2:
            return (0.0, 0.0)
        x0, y0 = self.history[0]
        x1, y1 = self.history[-1]
        n = max(len(self.history) - 1, 1)
        return ((x1 - x0) / n, (y1 - y0) / n)


@dataclass
class InferenceRequest:
    camera_id: str
    frame_id: int
    image: object
    model_key: str
    timestamp: float
