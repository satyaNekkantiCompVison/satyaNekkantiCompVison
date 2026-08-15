from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Insight:
    domain: str
    severity: str  # info | watch | action
    title: str
    recommendation: str
    camera_id: str = ""
    camera_name: str = ""
    evidence: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence"] = data.get("evidence") or {}
        return data


def _cam_name(cameras: list[dict[str, Any]], camera_id: str) -> str:
    for cam in cameras:
        if cam.get("id") == camera_id:
            return str(cam.get("name") or camera_id)
    return camera_id or "site"


def _events_in_window(events: list[dict[str, Any]], now: float, window_s: float, types: set[str] | None = None) -> list[dict[str, Any]]:
    start = now - window_s
    out = []
    for ev in events:
        ts = float(ev.get("ts") or 0)
        if ts < start:
            continue
        if types and ev.get("type") not in types:
            continue
        out.append(ev)
    return out


def _count_by_camera(events: list[dict[str, Any]], key: str | None = None, value: str | None = None) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for ev in events:
        if key and ev.get(key) != value:
            continue
        counts[str(ev.get("camera_id") or "unknown")] += 1
    return dict(counts)


def _rate_per_min(n: int, window_s: float) -> float:
    minutes = max(window_s / 60.0, 1e-6)
    return n / minutes


def summarize_events(events: list[dict[str, Any]], now: float | None = None) -> dict[str, Any]:
    if now is None:
        now = max((float(e.get("ts") or 0) for e in events), default=0.0)
    by_type: dict[str, int] = defaultdict(int)
    by_camera: dict[str, int] = defaultdict(int)
    hourly: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for ev in events:
        t = str(ev.get("type") or "unknown")
        cam = str(ev.get("camera_id") or "unknown")
        by_type[t] += 1
        by_camera[cam] += 1
        ts = float(ev.get("ts") or 0)
        hour = int(ts // 3600) * 3600
        hourly[str(hour)][t] += 1
    recent_5 = _events_in_window(events, now, 300)
    recent_15 = _events_in_window(events, now, 900)
    return {
        "total": len(events),
        "by_type": dict(by_type),
        "by_camera": dict(by_camera),
        "last_5min": len(recent_5),
        "last_15min": len(recent_15),
        "hourly": {k: dict(v) for k, v in sorted(hourly.items())},
    }


def generate_insights(
    events: list[dict[str, Any]],
    cameras: list[dict[str, Any]] | None = None,
    now: float | None = None,
) -> list[Insight]:
    """Turn accumulated detections into staffing, inventory, and traffic actions."""
    cameras = cameras or []
    if now is None:
        now = max((float(e.get("ts") or 0) for e in events), default=0.0) or 0.0
    insights: list[Insight] = []
    insights.extend(_store_insights(events, cameras, now))
    insights.extend(_traffic_insights(events, cameras, now))
    insights.extend(_fire_insights(events, cameras, now))
    order = {"action": 0, "watch": 1, "info": 2}
    insights.sort(key=lambda i: (order.get(i.severity, 9), i.domain, i.camera_id))
    return insights


def _store_insights(events: list[dict[str, Any]], cameras: list[dict[str, Any]], now: float) -> list[Insight]:
    out: list[Insight] = []
    enters_5 = _events_in_window(events, now, 300, {"people_count"})
    enters_15 = _events_in_window(events, now, 900, {"people_count"})
    prev_15 = _events_in_window(events, now - 900, 900, {"people_count"})

    def _kind(evs: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
        return [e for e in evs if e.get("kind") == kind]

    in_5 = _kind(enters_5, "enter")
    in_15 = _kind(enters_15, "enter")
    in_prev = _kind(prev_15, "enter")
    by_cam_5 = _count_by_camera(in_5)
    by_cam_15 = _count_by_camera(in_15)
    by_cam_prev = _count_by_camera(in_prev)

    cam_ids = set(by_cam_15) | set(by_cam_5) | {c["id"] for c in cameras if c.get("store")}
    for cam_id in sorted(cam_ids):
        name = _cam_name(cameras, cam_id)
        n5 = by_cam_5.get(cam_id, 0)
        n15 = by_cam_15.get(cam_id, 0)
        nprev = by_cam_prev.get(cam_id, 0)
        rate5 = _rate_per_min(n5, 300)
        rate15 = _rate_per_min(n15, 900)
        occ = 0
        for cam in cameras:
            if cam.get("id") == cam_id and cam.get("store"):
                occ = int(cam["store"].get("occupancy") or 0)
        predicted_15 = round(rate5 * 15)
        surge = nprev > 0 and n15 >= int(nprev * 1.3) and n15 >= 6
        busy = rate5 >= 4 or occ >= 8 or n15 >= 12
        if surge or busy:
            cashiers = max(2, 1 + (occ + 7) // 8)
            stockers = 2 if surge or rate5 >= 6 else 1
            out.append(
                Insight(
                    domain="store",
                    severity="action" if surge or occ >= 10 or rate5 >= 6 else "watch",
                    title=f"Rising footfall at {name}",
                    recommendation=(
                        f"More shoppers are arriving ({n5} entries in 5 min, ~{rate5:.1f}/min). "
                        f"Expect about {predicted_15} arrivals in the next 15 minutes. "
                        f"Add staff now: {cashiers} cashiers/floor associates and {stockers} person(s) on replenishment "
                        "for high-velocity SKUs (checkout snacks, cold drinks, baskets)."
                    ),
                    camera_id=cam_id,
                    camera_name=name,
                    evidence={
                        "entries_5min": n5,
                        "entries_15min": n15,
                        "entries_prior_15min": nprev,
                        "rate_per_min": round(rate5, 2),
                        "occupancy": occ,
                        "predicted_arrivals_15min": predicted_15,
                        "suggested_cashiers": cashiers,
                        "suggested_replenishment": stockers,
                    },
                )
            )
        elif n15 >= 3:
            out.append(
                Insight(
                    domain="store",
                    severity="info",
                    title=f"Steady traffic at {name}",
                    recommendation=(
                        f"{n15} entries in 15 min (~{rate15:.1f}/min), occupancy {occ}. "
                        "Keep standard staffing; watch the next 10 minutes for a lunch/evening surge."
                    ),
                    camera_id=cam_id,
                    camera_name=name,
                    evidence={"entries_15min": n15, "occupancy": occ, "rate_per_min": round(rate15, 2)},
                )
            )
    if not cam_ids and any(c.get("store") for c in cameras):
        out.append(
            Insight(
                domain="store",
                severity="info",
                title="Collecting store traffic",
                recommendation="People-count events will drive staffing and inventory suggestions as shoppers cross the entrance line.",
            )
        )
    covered = {i.camera_id for i in out if i.camera_id}
    for cam in cameras:
        store = cam.get("store")
        if not store or cam.get("id") in covered:
            continue
        ins = int(store.get("in_count") or 0)
        occ = int(store.get("occupancy") or 0)
        if ins < 5 and occ < 3:
            continue
        name = _cam_name(cameras, cam["id"])
        cashiers = max(2, 1 + (max(occ, ins // 4) + 7) // 8)
        out.append(
            Insight(
                domain="store",
                severity="watch" if ins >= 10 or occ >= 6 else "info",
                title=f"Accumulated visits at {name}",
                recommendation=(
                    f"{ins} entries counted this session, {occ} people on the floor now. "
                    f"Prepare inventory at the front and keep {cashiers} associates available; "
                    "a further wave typically follows 10–20 minutes after the first surge."
                ),
                camera_id=cam["id"],
                camera_name=name,
                evidence={"in_count": ins, "out_count": store.get("out_count"), "occupancy": occ},
            )
        )
    return out


def _traffic_insights(events: list[dict[str, Any]], cameras: list[dict[str, Any]], now: float) -> list[Insight]:
    out: list[Insight] = []
    cross_15 = _events_in_window(events, now, 900, {"vehicle_crossing"})
    wrong_15 = _events_in_window(events, now, 900, {"wrong_way"})
    jump_15 = _events_in_window(events, now, 900, {"signal_jump"})
    wrong_all = [e for e in events if e.get("type") == "wrong_way"]
    cross_all = [e for e in events if e.get("type") == "vehicle_crossing"]

    by_cross = _count_by_camera(cross_15)
    by_wrong = _count_by_camera(wrong_15)
    by_jump = _count_by_camera(jump_15)
    by_wrong_all = _count_by_camera(wrong_all)
    by_cross_all = _count_by_camera(cross_all)

    cam_ids = set(by_cross) | set(by_wrong) | set(by_jump) | {c["id"] for c in cameras if c.get("traffic")}
    if by_wrong_all:
        hotspot = max(by_wrong_all.items(), key=lambda kv: kv[1])
        if hotspot[1] >= 3:
            name = _cam_name(cameras, hotspot[0])
            share = hotspot[1] / max(sum(by_wrong_all.values()), 1)
            out.append(
                Insight(
                    domain="traffic",
                    severity="action",
                    title=f"Wrong-way hotspot: {name}",
                    recommendation=(
                        f"{hotspot[1]} wrong-way events are concentrated at this signal "
                        f"({share:.0%} of all wrong-way detections). "
                        "Prioritize this junction for extra enforcement, clearer one-way markings, "
                        "and a review of allowed_direction in the camera config."
                    ),
                    camera_id=hotspot[0],
                    camera_name=name,
                    evidence={"wrong_way_total": hotspot[1], "share": round(share, 3), "by_signal": by_wrong_all},
                )
            )

    for cam_id in sorted(cam_ids):
        name = _cam_name(cameras, cam_id)
        n_cross = by_cross.get(cam_id, 0)
        n_wrong = by_wrong.get(cam_id, 0)
        n_jump = by_jump.get(cam_id, 0)
        rate = _rate_per_min(n_cross, 900)
        snapshot = {}
        for cam in cameras:
            if cam.get("id") == cam_id and cam.get("traffic"):
                snapshot = cam["traffic"]
        if n_cross >= 10 or rate >= 8 or int(snapshot.get("vehicles_crossed") or 0) >= 20:
            out.append(
                Insight(
                    domain="traffic",
                    severity="watch" if n_jump < 3 else "action",
                    title=f"Heavy traffic at {name}",
                    recommendation=(
                        f"{n_cross} vehicles crossed in 15 min (~{rate:.1f}/min). "
                        "Expect queues: extend green time if the controller allows, warn downstream signals, "
                        "and hold non-urgent maintenance. "
                        + (f"{n_jump} red-light jumps in the same window — add a visible stop-line reminder." if n_jump else "")
                    ),
                    camera_id=cam_id,
                    camera_name=name,
                    evidence={
                        "crossings_15min": n_cross,
                        "rate_per_min": round(rate, 2),
                        "signal_jumps_15min": n_jump,
                        "wrong_way_15min": n_wrong,
                        "signal_color": snapshot.get("signal_color"),
                    },
                )
            )
        elif n_wrong >= 2 and not any(i.camera_id == cam_id and "Wrong-way" in i.title for i in out):
            out.append(
                Insight(
                    domain="traffic",
                    severity="watch",
                    title=f"Wrong-way activity at {name}",
                    recommendation=(
                        f"{n_wrong} wrong-way movements in 15 min "
                        f"({by_wrong_all.get(cam_id, n_wrong)} all-time at this signal). "
                        "Check lane arrows and whether the allowed flow in config matches the roadway."
                    ),
                    camera_id=cam_id,
                    camera_name=name,
                    evidence={"wrong_way_15min": n_wrong, "wrong_way_total": by_wrong_all.get(cam_id, 0)},
                )
            )
        elif n_cross >= 3:
            out.append(
                Insight(
                    domain="traffic",
                    severity="info",
                    title=f"Moderate flow at {name}",
                    recommendation=f"{n_cross} crossings in 15 min. Traffic is manageable; keep monitoring signal jumps.",
                    camera_id=cam_id,
                    camera_name=name,
                    evidence={"crossings_15min": n_cross, "crossings_total": by_cross_all.get(cam_id, 0)},
                )
            )
    covered = {i.camera_id for i in out if i.camera_id}
    for cam in cameras:
        tr = cam.get("traffic")
        if not tr or cam.get("id") in covered:
            continue
        crossed = int(tr.get("vehicles_crossed") or 0)
        wrong = int(tr.get("wrong_way") or 0)
        jumps = int(tr.get("signal_jumps") or 0)
        name = _cam_name(cameras, cam["id"])
        if wrong >= 2:
            out.append(
                Insight(
                    domain="traffic",
                    severity="action",
                    title=f"Wrong-way cluster at {name}",
                    recommendation=(
                        f"{wrong} wrong-way detections at this signal. "
                        "Treat it as the priority junction: verify one-way signage, "
                        "and brief traffic police / control-room staff for this approach."
                    ),
                    camera_id=cam["id"],
                    camera_name=name,
                    evidence={"wrong_way": wrong, "vehicles_crossed": crossed, "signal_jumps": jumps},
                )
            )
        elif crossed >= 8:
            out.append(
                Insight(
                    domain="traffic",
                    severity="watch",
                    title=f"Heavy volume at {name}",
                    recommendation=(
                        f"{crossed} vehicles have crossed this stop line. "
                        "Plan for congestion: stagger nearby signal timing and avoid lane closures here."
                    ),
                    camera_id=cam["id"],
                    camera_name=name,
                    evidence={"vehicles_crossed": crossed, "signal_jumps": jumps, "signal_color": tr.get("signal_color")},
                )
            )
    return out


def _fire_insights(events: list[dict[str, Any]], cameras: list[dict[str, Any]], now: float) -> list[Insight]:
    recent = _events_in_window(events, now, 600, {"fire_smoke_alert"})
    if not recent:
        return []
    last = max(recent, key=lambda e: float(e.get("ts") or 0))
    cam = str(last.get("camera_id") or "")
    name = _cam_name(cameras, cam)
    kind = last.get("kind") or "fire"
    return [
        Insight(
            domain="fire",
            severity="action",
            title=f"{kind.replace('_', ' ').title()} alert at {name}",
            recommendation=(
                f"{len(recent)} fire/smoke alert(s) in the last 10 minutes. "
                "Dispatch security, verify the camera view, and keep the aisle/exit clear."
            ),
            camera_id=cam,
            camera_name=name,
            evidence={"alerts_10min": len(recent), "kind": kind, "confidence": last.get("confidence")},
        )
    ]
