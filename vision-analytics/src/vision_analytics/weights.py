from __future__ import annotations

import os
import urllib.error
import urllib.request
from pathlib import Path

COCO_URLS = [
    "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt",
]

# keremberke/yolov8n-fire-and-smoke-detection now returns HTTP 401 without a token.
# Prefer public GitHub + ungated Hugging Face mirrors.
FIRE_URLS = [
    "https://github.com/Nocluee100/Fire-and-Smoke-Detection-yolov8-v1/raw/main/weights/best.pt",
    "https://huggingface.co/rabahdev/fire-smoke-yolov8n/resolve/main/best.pt",
    "https://huggingface.co/keremberke/yolov8n-fire-and-smoke-detection/resolve/main/best.pt",
]

MIN_CHECKPOINT_BYTES = 1_000_000


def is_valid_checkpoint(path: Path) -> bool:
    if not path.is_file():
        return False
    size = path.stat().st_size
    if size < MIN_CHECKPOINT_BYTES:
        return False
    with path.open("rb") as fh:
        magic = fh.read(2)
    # Ultralytics .pt files are zip archives (PK) wrapping a pickle.
    return magic == b"PK"


def _request(url: str) -> urllib.request.Request:
    headers = {
        "User-Agent": "vision-analytics/0.1 (+https://github.com/ultralytics)",
        "Accept": "*/*",
    }
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if token and "huggingface.co" in url:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def download_url(url: str, dest: Path, timeout: int = 120) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = _request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp, tmp.open("wb") as out:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
    tmp.replace(dest)


def download_file(url: str, dest: Path, timeout: int = 120) -> None:
    download_url(url, dest, timeout=timeout)
    if not is_valid_checkpoint(dest):
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"downloaded file from {url} is not a valid YOLO checkpoint")


def download_first_available(urls: list[str], dest: Path) -> str:
    errors: list[str] = []
    for url in urls:
        try:
            download_file(url, dest)
            return url
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, RuntimeError, OSError) as exc:
            errors.append(f"{url}: {exc}")
            dest.unlink(missing_ok=True)
            dest.with_suffix(dest.suffix + ".part").unlink(missing_ok=True)
    raise RuntimeError("all download mirrors failed:\n" + "\n".join(errors))


def ensure_weights(path: str | Path, urls: list[str] | None = None) -> Path:
    dest = Path(path)
    if is_valid_checkpoint(dest):
        return dest
    if not urls:
        raise FileNotFoundError(f"missing weights {dest} and no download URL configured")
    used = download_first_available(urls, dest)
    print(f"Downloaded {used} -> {dest}")
    return dest
