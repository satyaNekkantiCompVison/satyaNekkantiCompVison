from __future__ import annotations

import time

import numpy as np

from vision_analytics.config import EngineConfig
from vision_analytics.inference.models import ScriptedDetector
from vision_analytics.inference.pool import SharedInferenceEngine
from vision_analytics.types import Detection


def test_shared_engine_batches_multiple_cameras():
    det = Detection(xyxy=(0, 0, 10, 10), conf=0.8, cls_id=0, label="person")
    model = ScriptedDetector([det])
    engine = SharedInferenceEngine(
        {"coco": model},
        EngineConfig(max_batch_size=8, max_batch_wait_ms=20, workers=1),
    )
    engine.start()
    frames = [np.zeros((64, 64, 3), dtype=np.uint8) for _ in range(6)]
    futs = [engine.submit(f"cam-{i}", "coco", frames[i]) for i in range(6)]
    results = [f.result(timeout=2) for f in futs]
    engine.stop()
    assert all(r and r[0].label == "person" for r in results)
    assert all(r[0].camera_id.startswith("cam-") for r in results)
    assert model.calls >= 1
    # Dynamic batching should collapse several frames into fewer GPU calls.
    assert model.calls < 6
    stats = engine.stats()
    assert stats["total_frames"] >= 6
    time.sleep(0.01)
