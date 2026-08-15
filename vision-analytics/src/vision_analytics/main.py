from __future__ import annotations

import argparse
import logging
from pathlib import Path

import uvicorn

from vision_analytics.config import CameraConfig, load_config
from vision_analytics.pipeline import AnalyticsPipeline
from vision_analytics.api import create_app


def demo_cameras() -> list[CameraConfig]:
    return [
        CameraConfig(
            id="store-demo",
            name="Store entrance (demo)",
            source="synthetic://store",
            modules=["store", "fire"],
            sample_fps=15,
        ),
        CameraConfig(
            id="aisle-demo",
            name="Aisle heat map (demo)",
            source="synthetic://store",
            modules=["store"],
            sample_fps=12,
        ),
        CameraConfig(
            id="traffic-demo",
            name="Junction signal (demo)",
            source="synthetic://traffic",
            modules=["traffic"],
            sample_fps=20,
        ),
        CameraConfig(
            id="fire-demo",
            name="Fire watch (demo)",
            source="synthetic://fire",
            modules=["fire"],
            sample_fps=10,
        ),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Shared-GPU CCTV vision analytics")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--cameras", default="configs/cameras.yaml")
    parser.add_argument("--demo", action="store_true", help="Run synthetic cameras (no RTSP required)")
    parser.add_argument("--mock", action="store_true", help="Skip YOLO weights (CI / no GPU)")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = Path(__file__).resolve().parents[2]
    config_path = Path(args.config)
    cameras_path = Path(args.cameras)
    if not config_path.is_absolute():
        config_path = (Path.cwd() / config_path)
        if not config_path.exists():
            config_path = root / args.config
    if not cameras_path.is_absolute():
        cameras_path = Path.cwd() / cameras_path
        if not cameras_path.exists():
            cameras_path = root / args.cameras

    cfg = load_config(config_path, cameras_path)
    if args.demo or not any(c.enabled for c in cfg.cameras):
        cfg.cameras = demo_cameras()

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
