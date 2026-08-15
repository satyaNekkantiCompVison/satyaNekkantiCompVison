from __future__ import annotations

from pathlib import Path

from vision_analytics.demo_sources import is_video_file
from vision_analytics.ingest.rtsp import FrameSource
from vision_analytics.main import demo_cameras, synthetic_cameras


def test_is_video_file_mp4_and_ogg(tmp_path: Path):
    mp4 = tmp_path / "a.mp4"
    mp4.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"\x00" * 20_000)
    assert is_video_file(mp4)
    ogg = tmp_path / "a.ogv"
    ogg.write_bytes(b"OggS" + b"\x00" * 20_000)
    assert is_video_file(ogg)
    tiny = tmp_path / "tiny.mp4"
    tiny.write_bytes(b"\x00\x00\x00\x18ftyp")
    assert not is_video_file(tiny)


def test_webcam_is_not_loopable():
    src = FrameSource("cam", "0", 5)
    assert src._is_loopable() is False
    file_src = FrameSource("cam", "samples/store-aisle-detection.mp4", 5)
    assert file_src._is_loopable() is True
    rtsp = FrameSource("cam", "rtsp://127.0.0.1:8554/x", 5)
    assert rtsp._is_loopable() is False


def test_demo_cameras_fall_back_when_clips_missing(tmp_path: Path):
    cams = demo_cameras(tmp_path)
    assert all(c.source.startswith("synthetic://") for c in cams)
    ids = {c.id for c in synthetic_cameras()}
    assert {c.id for c in cams} == ids
