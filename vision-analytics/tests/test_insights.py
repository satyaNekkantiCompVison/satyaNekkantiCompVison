from __future__ import annotations

from vision_analytics.insights import generate_insights, summarize_events


def _enter(cam: str, ts: float, n: int = 1) -> list[dict]:
    return [
        {"type": "people_count", "kind": "enter", "camera_id": cam, "ts": ts + i, "in_count": i + 1, "occupancy": 4}
        for i in range(n)
    ]


def test_store_surge_recommends_staff_and_inventory():
    now = 10_000.0
    events = _enter("lobby", now - 200, 12)
    events += _enter("lobby", now - 1200, 4)
    cameras = [{"id": "lobby", "name": "Lobby", "store": {"occupancy": 11, "in_count": 16, "out_count": 5}}]
    insights = generate_insights(events, cameras, now=now)
    store = [i for i in insights if i.domain == "store"]
    assert store
    text = " ".join(i.recommendation.lower() for i in store)
    assert "staff" in text or "cashiers" in text
    assert any(i.severity in {"action", "watch"} for i in store)
    assert any("inventory" in i.recommendation.lower() or "replenish" in i.recommendation.lower() or "sku" in i.recommendation.lower() for i in store)


def test_wrong_way_hotspot_and_heavy_traffic():
    now = 20_000.0
    events = []
    for i in range(8):
        events.append({"type": "wrong_way", "camera_id": "junction-a", "ts": now - 60, "label": "car"})
    for i in range(2):
        events.append({"type": "wrong_way", "camera_id": "junction-b", "ts": now - 60, "label": "car"})
    for i in range(15):
        events.append({"type": "vehicle_crossing", "camera_id": "junction-a", "ts": now - 30, "label": "car"})
    cameras = [
        {"id": "junction-a", "name": "Main & 5th", "traffic": {"vehicles_crossed": 40, "wrong_way": 8, "signal_jumps": 1}},
        {"id": "junction-b", "name": "Side street", "traffic": {"vehicles_crossed": 3, "wrong_way": 2, "signal_jumps": 0}},
    ]
    insights = generate_insights(events, cameras, now=now)
    traffic = [i for i in insights if i.domain == "traffic"]
    titles = " ".join(i.title.lower() for i in traffic)
    recs = " ".join(i.recommendation.lower() for i in traffic)
    assert "wrong-way" in titles or "wrong-way" in recs
    assert "junction-a" in " ".join(i.camera_id for i in traffic)
    assert "heavy" in titles or "congest" in recs or "queue" in recs or "volume" in titles


def test_summarize_counts_types():
    events = [
        {"type": "people_count", "camera_id": "a", "ts": 1},
        {"type": "wrong_way", "camera_id": "b", "ts": 2},
        {"type": "wrong_way", "camera_id": "b", "ts": 3},
    ]
    s = summarize_events(events, now=3)
    assert s["total"] == 3
    assert s["by_type"]["wrong_way"] == 2
    assert s["by_camera"]["b"] == 2
