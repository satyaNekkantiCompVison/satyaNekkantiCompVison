from __future__ import annotations

import argparse
import logging
from pathlib import Path

import uvicorn

from vision_analytics.config import CameraConfig, FireModuleConfig, StoreModuleConfig, TrafficModuleConfig, load_config
from vision_analytics.demo_sources import download_demo_clips, samples_dir
from vision_analytics.pipeline import AnalyticsPipeline
from vision_analytics.api import create_app


def _clip(root: Path, kind: str) -> Path:
    from vision_analytics.demo_sources import DEMO_CLIPS

    return samples_dir(root) / DEMO_CLIPS[kind]["file"]


def synthetic_cameras() -> list[CameraConfig]:
    return [
        CameraConfig(
            id="store-demo",
            name="Store entrance (synthetic)",
            source="synthetic://store",
            modules=["store", "fire"],
            sample_fps=15,
        ),
        CameraConfig(
            id="aisle-demo",
            name="Aisle heat map (synthetic)",
            source="synthetic://store",
            modules=["store"],
            sample_fps=12,
        ),
        CameraConfig(
            id="traffic-demo",
            name="Junction signal (synthetic)",
            source="synthetic://traffic",
            modules=["traffic"],
            sample_fps=20,
        ),
        CameraConfig(
            id="fire-demo",
            name="Fire watch (synthetic)",
            source="synthetic://fire",
            modules=["fire"],
            sample_fps=10,
        ),
    ]


def demo_cameras(root: Path | None = None) -> list[CameraConfig]:
    """Customer demo: looping real sample videos (Intel + Wikimedia)."""
    base = Path(root) if root else Path.cwd()
    store = _clip(base, "store")
    people = _clip(base, "people")
    traffic = _clip(base, "traffic")
    fire = _clip(base, "fire")
    missing = [p for p in (store, people, traffic, fire) if not p.exists()]
    if missing:
        logging.getLogger(__name__).warning("sample clips missing %s — using synthetic fallback", missing)
        return synthetic_cameras()
    return [
        CameraConfig(
            id="store-demo",
            name="Store aisle (sample CCTV)",
            source=str(store),
            modules=["store"],
            sample_fps=12,
            store=StoreModuleConfig(
                count_line=[[0.15, 0.62], [0.85, 0.62]],
                in_direction="down",
                heatmap_bins=[64, 36],
            ),
        ),
        CameraConfig(
            id="people-demo",
            name="Pedestrian plaza (sample CCTV)",
            source=str(people),
            modules=["store"],
            sample_fps=12,
            store=StoreModuleConfig(
                count_line=[[0.10, 0.70], [0.90, 0.70]],
                in_direction="down",
                heatmap_bins=[80, 45],
            ),
        ),
        CameraConfig(
            id="traffic-demo",
            name="Road / vehicles (sample CCTV)",
            source=str(traffic),
            modules=["traffic"],
            sample_fps=15,
            traffic=TrafficModuleConfig(
                allowed_direction="left_to_right",
                stop_line=[[0.08, 0.72], [0.92, 0.72]],
                signal_roi=[0.70, 0.04, 0.92, 0.22],
                min_track_age=4,
                wrong_way_dot=-0.35,
            ),
        ),
        CameraConfig(
            id="fire-demo",
            name="Fire watch (sample video)",
            source=str(fire),
            modules=["fire"],
            sample_fps=10,
            fire=FireModuleConfig(conf=0.25, cooldown_sec=6),
        ),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Shared-GPU CCTV vision analytics")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--cameras", default="configs/cameras.yaml")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Customer demo: download and loop real sample CCTV videos (store, people, traffic, fire)",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Use generated scenes instead of real sample videos",
    )
    parser.add_argument("--mock", action="store_true", help="Skip YOLO weights (CI / no GPU)")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = Path(__file__).resolve().parents[2]
    config_path = Path(args.config)
    cameras_path = Path(args.cameras)
    if not config_path.is_absolute():
        config_path = Path.cwd() / config_path
        if not config_path.exists():
            config_path = root / args.config
    if not cameras_path.is_absolute():
        cameras_path = Path.cwd() / cameras_path
        if not cameras_path.exists():
            cameras_path = root / args.cameras

    cfg = load_config(config_path, cameras_path)
    if args.synthetic:
        cfg.cameras = synthetic_cameras()
    elif args.demo:
        logging.getLogger(__name__).info("Downloading licensed sample CCTV clips for the customer demo...")
        download_demo_clips(root)
        cfg.cameras = demo_cameras(root)

    pipeline = AnalyticsPipeline(cfg, mock=args.mock)
    pipeline.start()
    app = create_app(pipeline)
    host = args.host or cfg.dashboard.host
    port = args.port or cfg.dashboard.port
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    finally:
        pipeline.stop()


if __name__ == "__main__":
    main()
