from __future__ import annotations

from fastapi.testclient import TestClient

from vision_analytics.api import create_app
from vision_analytics.config import AppConfig, EngineConfig
from vision_analytics.main import demo_cameras
from vision_analytics.pipeline import AnalyticsPipeline


def test_health_and_cameras_with_mock_pipeline(tmp_path):
    cfg = AppConfig(
        engine=EngineConfig(device="cpu", half=False, max_batch_size=4, max_batch_wait_ms=5),
        cameras=demo_cameras(),
        storage={"sqlite_path": str(tmp_path / "e.db"), "snapshot_dir": str(tmp_path / "snap")},
    )
    pipe = AnalyticsPipeline(cfg, mock=True)
    pipe.start()
    try:
        app = create_app(pipe)
        client = TestClient(app)
        health = client.get("/api/health").json()
        assert health["ok"] is True
        cams = client.get("/api/cameras").json()
        ids = {c["id"] for c in cams}
        assert {"store-demo", "traffic-demo", "fire-demo"} <= ids
        events = client.get("/api/events").json()
        assert isinstance(events, list)
    finally:
        pipe.stop()
