from __future__ import annotations

from vision_analytics.analytics.fire_smoke import FireSmokeAnalyzer
from vision_analytics.config import FireModuleConfig
from vision_analytics.types import Detection


def test_fire_alert_and_cooldown():
    an = FireSmokeAnalyzer("f1", FireModuleConfig(conf=0.4, cooldown_sec=10))
    fire = Detection(xyxy=(1, 1, 10, 10), conf=0.9, cls_id=0, label="fire")
    ev1 = an.update([fire], now=100)
    assert ev1 and ev1[0]["type"] == "fire_smoke_alert"
    ev2 = an.update([fire], now=101)
    assert ev2 == []
    ev3 = an.update([fire], now=111)
    assert ev3


def test_smoke_only_is_high_not_critical():
    an = FireSmokeAnalyzer("f1", FireModuleConfig(conf=0.3, cooldown_sec=0))
    smoke = Detection(xyxy=(1, 1, 8, 8), conf=0.5, cls_id=1, label="smoke")
    ev = an.update([smoke], now=1)
    assert ev[0]["severity"] == "high"
    assert ev[0]["kind"] == "smoke"
