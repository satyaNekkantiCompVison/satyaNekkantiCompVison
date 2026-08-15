from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from vision_analytics.config import FireModuleConfig
from vision_analytics.types import Detection


@dataclass
class FireSmokeState:
    last_alert_ts: float = 0.0
    fire_count: int = 0
    smoke_count: int = 0
    last_detections: list[Detection] = field(default_factory=list)


class FireSmokeAnalyzer:
    """Alerts on pretrained fire/smoke YOLO detections with cooldown."""

    def __init__(self, camera_id: str, cfg: FireModuleConfig) -> None:
        self.camera_id = camera_id
        self.cfg = cfg
        self.state = FireSmokeState()

    def update(self, detections: list[Detection], now: float | None = None) -> list[dict[str, Any]]:
        now = now if now is not None else time.time()
        fires = [d for d in detections if d.label.lower() in {"fire", "flame"} and d.conf >= self.cfg.conf]
        smokes = [d for d in detections if d.label.lower() == "smoke" and d.conf >= self.cfg.conf]
        self.state.fire_count = len(fires)
        self.state.smoke_count = len(smokes)
        self.state.last_detections = fires + smokes
        events: list[dict[str, Any]] = []
        if not fires and not smokes:
            return events
        if now - self.state.last_alert_ts < self.cfg.cooldown_sec:
            return events
        self.state.last_alert_ts = now
        kind = "fire" if fires else "smoke"
        if fires and smokes:
            kind = "fire_and_smoke"
        best = max(fires + smokes, key=lambda d: d.conf)
        events.append(
            {
                "type": "fire_smoke_alert",
                "severity": "critical" if fires else "high",
                "camera_id": self.camera_id,
                "kind": kind,
                "confidence": round(best.conf, 3),
                "bbox": list(best.xyxy),
                "fire_count": len(fires),
                "smoke_count": len(smokes),
                "ts": now,
            }
        )
        return events

    def snapshot(self) -> dict[str, Any]:
        return {
            "fire_count": self.state.fire_count,
            "smoke_count": self.state.smoke_count,
            "active": bool(self.state.last_detections),
        }
