from __future__ import annotations

from pathlib import Path

from vision_analytics.weights import download_url

# Licensed clips for customer demos (not random exposed CCTV).
# Intel OpenVINO sample-videos: https://github.com/intel-iot-devkit/sample-videos
# Wikimedia Commons fire clip: CC-licensed.
DEMO_CLIPS: dict[str, dict[str, str]] = {
    "store": {
        "file": "store-aisle-detection.mp4",
        "url": "https://github.com/intel-iot-devkit/sample-videos/raw/master/store-aisle-detection.mp4",
        "license": "Intel IoT sample video (store aisle / people)",
    },
    "people": {
        "file": "people-detection.mp4",
        "url": "https://github.com/intel-iot-devkit/sample-videos/raw/master/people-detection.mp4",
        "license": "Intel IoT sample video (pedestrians)",
    },
    "traffic": {
        "file": "person-bicycle-car-detection.mp4",
        "url": "https://github.com/intel-iot-devkit/sample-videos/raw/master/person-bicycle-car-detection.mp4",
        "license": "Intel IoT sample video (vehicles + people)",
    },
    "cars": {
        "file": "car-detection.mp4",
        "url": "https://github.com/intel-iot-devkit/sample-videos/raw/master/car-detection.mp4",
        "license": "Intel IoT sample video (vehicles)",
    },
    "fire": {
        "file": "fire-burning.ogv",
        "url": "https://upload.wikimedia.org/wikipedia/commons/e/e8/Fire_burning.ogv",
        "license": "Wikimedia Commons — Fire burning.ogv",
    },
}

PUBLIC_RTSP = [
    {
        "id": "wowza-rtsp-test",
        "name": "Wowza public RTSP test (protocol check)",
        "source": "rtsp://9627b0bf2a7b.entrypoint.cloud.wowza.com:1935/app-p5260J38/66abe4b9_stream1",
        "note": "Official Wowza looping test stream. Enable to prove RTSP ingest; it is not fire/store/traffic footage.",
    }
]


def is_video_file(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 10_000:
        return False
    with path.open("rb") as fh:
        magic = fh.read(12)
    return magic[4:8] == b"ftyp" or magic[:4] == b"OggS" or magic[:4] == b"\x1aE\xdf\xa3" or magic[:4] == b"RIFF"


def samples_dir(root: Path | None = None) -> Path:
    base = Path(root) if root else Path.cwd()
    return base if base.name == "samples" else base / "samples"


def download_demo_clips(root: Path | None = None, kinds: list[str] | None = None) -> dict[str, Path]:
    dest_dir = samples_dir(root)
    dest_dir.mkdir(parents=True, exist_ok=True)
    wanted = kinds or ["store", "people", "traffic", "fire"]
    out: dict[str, Path] = {}
    for kind in wanted:
        meta = DEMO_CLIPS[kind]
        path = dest_dir / meta["file"]
        if is_video_file(path):
            print(f"Already have {path}")
            out[kind] = path
            continue
        print(f"Downloading {kind} clip from {meta['url']}")
        download_url(meta["url"], path, timeout=180)
        if not is_video_file(path):
            path.unlink(missing_ok=True)
            raise RuntimeError(f"invalid video downloaded for {kind}: {path}")
        print(f"Saved {path} ({path.stat().st_size} bytes) — {meta['license']}")
        out[kind] = path
    return out
