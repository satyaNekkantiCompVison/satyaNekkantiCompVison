from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest

from vision_analytics.weights import (
    download_first_available,
    is_valid_checkpoint,
)


class _FakeResp(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_is_valid_checkpoint(tmp_path: Path):
    good = tmp_path / "ok.pt"
    good.write_bytes(b"PK" + b"\x00" * 1_000_001)
    assert is_valid_checkpoint(good)
    bad = tmp_path / "bad.pt"
    bad.write_bytes(b"version https://git-lfs.github.com/spec/v1\n")
    assert not is_valid_checkpoint(bad)


def test_download_skips_401_and_uses_next_mirror(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import urllib.error
    import vision_analytics.weights as weights

    dest = tmp_path / "fire.pt"
    calls: list[str] = []

    def fake_urlopen(req, timeout=120):
        url = req.full_url if hasattr(req, "full_url") else req
        calls.append(str(url))
        if "gated" in str(url):
            raise urllib.error.HTTPError(str(url), 401, "Unauthorized", hdrs=None, fp=None)  # type: ignore[arg-type]
        payload = b"PK" + b"\x00" * 1_000_001
        return _FakeResp(payload)

    monkeypatch.setattr(weights.urllib.request, "urlopen", fake_urlopen)
    used = download_first_available(
        ["https://example.com/gated/best.pt", "https://example.com/public/best.pt"],
        dest,
    )
    assert used.endswith("/public/best.pt")
    assert dest.exists()
    assert is_valid_checkpoint(dest)
    assert any("gated" in u for u in calls)
