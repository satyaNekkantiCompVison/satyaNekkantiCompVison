from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class EngineConfig(BaseModel):
    device: str = "auto"
    half: bool = True
    target_fps: float = 90.0
    max_batch_size: int = 16
    max_batch_wait_ms: int = 8
    imgsz: int = 640
    conf: float = 0.35
    iou: float = 0.45
    workers: int = 1


class ModelSlotConfig(BaseModel):
    weights: str
    task: str = "detect"
    url: str | None = None
    classes: list[str] | None = None


class StorageConfig(BaseModel):
    sqlite_path: str = "data/events.db"
    snapshot_dir: str = "data/snapshots"


class DashboardConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8080


class StoreModuleConfig(BaseModel):
    count_line: list[list[float]] = Field(default_factory=lambda: [[0.2, 0.7], [0.8, 0.7]])
    in_direction: Literal["down", "up", "left", "right"] = "down"
    heatmap_bins: list[int] = Field(default_factory=lambda: [64, 36])


class TrafficModuleConfig(BaseModel):
    allowed_direction: Literal[
        "left_to_right", "right_to_left", "top_to_bottom", "bottom_to_top"
    ] = "left_to_right"
    stop_line: list[list[float]] = Field(default_factory=lambda: [[0.1, 0.8], [0.9, 0.8]])
    signal_roi: list[float] = Field(default_factory=lambda: [0.7, 0.05, 0.9, 0.25])
    min_track_age: int = 5
    wrong_way_dot: float = -0.35


class FireModuleConfig(BaseModel):
    conf: float = 0.4
    cooldown_sec: float = 8.0


class CameraConfig(BaseModel):
    id: str
    name: str
    enabled: bool = True
    source: str
    modules: list[Literal["store", "traffic", "fire"]] = Field(default_factory=list)
    sample_fps: float = 15.0
    store: StoreModuleConfig = Field(default_factory=StoreModuleConfig)
    traffic: TrafficModuleConfig = Field(default_factory=TrafficModuleConfig)
    fire: FireModuleConfig = Field(default_factory=FireModuleConfig)


class AppConfig(BaseModel):
    engine: EngineConfig = Field(default_factory=EngineConfig)
    models: dict[str, ModelSlotConfig] = Field(default_factory=dict)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    cameras: list[CameraConfig] = Field(default_factory=list)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_config(
    default_path: str | Path = "configs/default.yaml",
    cameras_path: str | Path = "configs/cameras.yaml",
) -> AppConfig:
    root = Path.cwd()
    default_file = Path(default_path)
    if not default_file.is_absolute():
        default_file = root / default_file
    cameras_file = Path(cameras_path)
    if not cameras_file.is_absolute():
        cameras_file = root / cameras_file
    if not cameras_file.exists():
        example = cameras_file.with_name("cameras.example.yaml")
        if example.exists():
            cameras_file = example

    data = _load_yaml(default_file)
    cam_data = _load_yaml(cameras_file)
    data["cameras"] = cam_data.get("cameras", [])
    return AppConfig.model_validate(data)
