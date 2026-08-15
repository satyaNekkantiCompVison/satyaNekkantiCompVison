#!/usr/bin/env python3
"""Download licensed sample CCTV clips for a customer demo (not random public cameras)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vision_analytics.demo_sources import DEMO_CLIPS, download_demo_clips  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--kinds", nargs="*", default=None, help=f"subset of {list(DEMO_CLIPS)}")
    args = parser.parse_args()
    clips = download_demo_clips(Path(args.root), kinds=args.kinds)
    print("Ready:")
    for kind, path in clips.items():
        print(f"  {kind}: {path}")


if __name__ == "__main__":
    main()
