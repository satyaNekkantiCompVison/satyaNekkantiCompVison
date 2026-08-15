#!/usr/bin/env python3
"""Fine-tune a pretrained YOLO checkpoint on a labeled dataset, then export.

Example (fire/smoke):
  python scripts/finetune.py --data datasets/fire/data.yaml --base weights/yolov8n-fire-smoke.pt --out runs/fire

Example (store people / traffic vehicles still start from COCO):
  python scripts/finetune.py --data datasets/traffic/data.yaml --base yolov8n.pt --out runs/traffic

The shared engine loads whatever .pt you point at in configs/default.yaml.
After fine-tune, copy best.pt over the production weights and restart.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Ultralytics data.yaml")
    parser.add_argument("--base", default="yolov8n.pt", help="Pretrained weights to start from")
    parser.add_argument("--out", default="runs/finetune")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="0")
    parser.add_argument("--export", choices=["none", "onnx", "engine"], default="none")
    args = parser.parse_args()

    from ultralytics import YOLO

    model = YOLO(args.base)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=args.out,
        name="train",
        pretrained=True,
    )
    best = Path(args.out) / "train" / "weights" / "best.pt"
    print(f"Fine-tuned weights: {best}")
    if args.export != "none" and best.exists():
        YOLO(str(best)).export(format=args.export, half=True, device=args.device)
        print(f"Exported {args.export} next to {best}")


if __name__ == "__main__":
    main()
