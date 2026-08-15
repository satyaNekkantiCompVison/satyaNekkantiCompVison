#!/usr/bin/env python3
"""Download pretrained YOLO checkpoints used by the shared inference engine."""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

COCO = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt"
FIRE = "https://huggingface.co/keremberke/yolov8n-fire-and-smoke-detection/resolve/main/best.pt"


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} -> {dest}")
    urllib.request.urlretrieve(url, dest)
    print(f"Saved {dest} ({dest.stat().st_size} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights-dir", default="weights")
    args = parser.parse_args()
    root = Path(args.weights_dir)
    _download(COCO, root / "yolov8n.pt")
    try:
        _download(FIRE, root / "yolov8n-fire-smoke.pt")
    except Exception as exc:
        print(f"Fire/smoke checkpoint download failed ({exc}).")
        print("Place a pretrained fire/smoke YOLO .pt at weights/yolov8n-fire-smoke.pt")
        print("COCO yolov8n still covers person/vehicle/traffic-light for store + traffic.")


if __name__ == "__main__":
    main()
