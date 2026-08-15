from __future__ import annotations

from pathlib import Path
from typing import Protocol

import numpy as np

from vision_analytics.types import Detection


class Detector(Protocol):
    names: dict[int, str]

    def predict_batch(
        self,
        images: list[np.ndarray],
        conf: float,
        iou: float,
        imgsz: int,
    ) -> list[list[Detection]]: ...


class UltralyticsDetector:
    """Thin wrapper around a pretrained Ultralytics YOLO checkpoint."""

    def __init__(
        self,
        weights: str,
        device: str,
        half: bool,
        class_filter: set[str] | None = None,
        names_override: dict[int, str] | None = None,
    ) -> None:
        from ultralytics import YOLO

        path = Path(weights)
        self.model = YOLO(str(path))
        self.device = device
        self.half = half and device != "cpu"
        self.class_filter = {c.lower() for c in class_filter} if class_filter else None
        self.names_override = names_override or {}
        raw_names = getattr(self.model, "names", {}) or {}
        if isinstance(raw_names, dict):
            self.names = {int(k): str(v) for k, v in raw_names.items()}
        else:
            self.names = {i: str(n) for i, n in enumerate(raw_names)}
        self.names.update(self.names_override)

    def predict_batch(
        self,
        images: list[np.ndarray],
        conf: float,
        iou: float,
        imgsz: int,
    ) -> list[list[Detection]]:
        if not images:
            return []
        results = self.model.predict(
            source=images,
            conf=conf,
            iou=iou,
            imgsz=imgsz,
            device=self.device,
            half=self.half,
            verbose=False,
            stream=False,
        )
        out: list[list[Detection]] = []
        for result in results:
            dets: list[Detection] = []
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                out.append(dets)
                continue
            xyxy = boxes.xyxy.cpu().numpy()
            confs = boxes.conf.cpu().numpy()
            clss = boxes.cls.cpu().numpy().astype(int)
            for box, score, cls_id in zip(xyxy, confs, clss, strict=False):
                label = self.names.get(int(cls_id), str(int(cls_id)))
                if self.class_filter and label.lower() not in self.class_filter:
                    continue
                dets.append(
                    Detection(
                        xyxy=(float(box[0]), float(box[1]), float(box[2]), float(box[3])),
                        conf=float(score),
                        cls_id=int(cls_id),
                        label=label,
                    )
                )
            out.append(dets)
        return out


class MockDetector:
    """Deterministic detector for tests and CPU-only CI."""

    def __init__(self, scripted: dict[str, list[Detection]] | None = None) -> None:
        self.names = {0: "person", 2: "car", 9: "traffic light", 80: "fire", 81: "smoke"}
        self.scripted = scripted or {}
        self.calls = 0

    def predict_batch(
        self,
        images: list[np.ndarray],
        conf: float,
        iou: float,
        imgsz: int,
    ) -> list[list[Detection]]:
        self.calls += 1
        return [[] for _ in images]


class ScriptedDetector:
    """Returns a canned detection list for every frame (unit tests)."""

    def __init__(self, detections: list[Detection]) -> None:
        self.names = {d.cls_id: d.label for d in detections}
        self.detections = detections
        self.calls = 0

    def predict_batch(
        self,
        images: list[np.ndarray],
        conf: float,
        iou: float,
        imgsz: int,
    ) -> list[list[Detection]]:
        self.calls += 1
        return [list(self.detections) for _ in images]


def resolve_device(preferred: str) -> str:
    if preferred and preferred != "auto":
        return preferred
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda:0"
    except Exception:
        pass
    return "cpu"


def load_detector(
    weights: str,
    device: str,
    half: bool,
    class_filter: set[str] | None = None,
    names_override: dict[int, str] | None = None,
    mock: bool = False,
) -> Detector:
    if mock:
        return MockDetector()
    return UltralyticsDetector(
        weights=weights,
        device=device,
        half=half,
        class_filter=class_filter,
        names_override=names_override,
    )
