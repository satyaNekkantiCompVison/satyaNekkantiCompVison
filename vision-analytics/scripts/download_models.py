#!/usr/bin/env python3
"""Download pretrained YOLO checkpoints used by the shared inference engine.

Fire/smoke defaults to public GitHub/Hugging Face mirrors because
keremberke/yolov8n-fire-and-smoke-detection currently returns HTTP 401
without a Hugging Face token. Set HF_TOKEN to also try gated HF repos.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vision_analytics.weights import COCO_URLS, FIRE_URLS, ensure_weights  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights-dir", default="weights")
    args = parser.parse_args()
    root = Path(args.weights_dir)
    coco = ensure_weights(root / "yolov8n.pt", COCO_URLS)
    print(f"COCO weights ready: {coco}")
    fire = ensure_weights(root / "yolov8n-fire-smoke.pt", FIRE_URLS)
    print(f"Fire/smoke weights ready: {fire}")


if __name__ == "__main__":
    main()
