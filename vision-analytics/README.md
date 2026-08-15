# Vision Analytics

Shared-GPU CCTV analytics for **fire/smoke**, **store** (people counting + heat map), and **traffic** (wrong-way, signal jump, vehicles crossing the stop line).

Cameras ingest RTSP (or files / webcam / synthetic demo). Frames are **batched on one YOLO process per GPU** so many streams share the same pretrained weights instead of loading a replica per camera. The engine is sized for about **90 FPS aggregate** (for example 6 × 15 FPS, or 3 × 30 FPS) via dynamic batching, FP16, and latest-frame drop.

```
RTSP / file / webcam          Shared GPU worker              Analytics
┌─────────────────┐           ┌──────────────────┐          ┌────────────────┐
│ cam-1  decode   │──┐        │  batch window    │          │ fire / smoke   │
│ cam-2  decode   │──┼─queue─▶│  YOLOv8n (COCO)  │─dets──▶  │ store count    │
│ cam-N  decode   │──┘        │  fire-smoke YOLO │          │ heat map       │
│ latest-frame    │           │  target ~90 FPS  │          │ wrong-way      │
│ drop (no lag)   │           └──────────────────┘          │ signal jump    │
└─────────────────┘                                         └───────┬────────┘
                                                                    │
                                                              FastAPI + WS
                                                              dashboard :8080
```

## Pretrained models (start here)

| Slot | Weights | Classes used |
| --- | --- | --- |
| `coco` | Ultralytics `yolov8n.pt` | person, bicycle, car, motorcycle, bus, truck, traffic light |
| `fire` | public YOLOv8n fire/smoke checkpoint (GitHub mirror; Hugging Face fallbacks) | fire, smoke |

Fine-tune later with `scripts/finetune.py` and point `configs/default.yaml` at `best.pt`. Optional TensorRT/ONNX export is on that same script (`--export engine`).

```bash
cd vision-analytics
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python scripts/download_models.py
```

If a Hugging Face URL returns **HTTP 401 Unauthorized**, that checkpoint is gated. The downloader already skips it and uses a public GitHub mirror (`Nocluee100/.../best.pt`) then `rabahdev/fire-smoke-yolov8n`. Optional: `export HF_TOKEN=...` to retry gated HF repos.

## Run the dashboard

Synthetic cameras (no RTSP required):

```bash
python -m vision_analytics.main --demo
```

Open [http://127.0.0.1:8080](http://127.0.0.1:8080).

Live RTSP:

1. Copy `configs/cameras.example.yaml` → `configs/cameras.yaml`
2. Set each `source` to `rtsp://user:pass@host:554/...`
3. Draw `count_line`, `stop_line`, and `signal_roi` in normalized 0–1 coordinates
4. `python -m vision_analytics.main --cameras configs/cameras.yaml`

GPU Docker:

```bash
docker compose up --build
```

## Shared GPU / 90 FPS

`SharedInferenceEngine` (`src/vision_analytics/inference/pool.py`):

- One CUDA worker (configurable) owns the weights
- Cameras submit frames; the worker packs up to `max_batch_size` (default 16) within `max_batch_wait_ms` (default 8 ms)
- Different modules share the same COCO model; fire/smoke is a second slot on the same GPU, not a second process per camera
- RTSP uses a **single-slot latest frame buffer** so a slow batch never queues seconds of lag
- Dashboard **GPU FPS** is aggregate throughput; `meeting_target` is true at ≥ 85% of `engine.target_fps`

Tune in `configs/default.yaml`: `imgsz`, `max_batch_size`, `half`, `sample_fps` per camera. For production 90 FPS on a mid-range GPU, keep `imgsz` at 640 with `yolov8n` (or export TensorRT). Larger models (`s`/`m`) trade FPS for recall — swap the weights path only.

## Modules

**Fire & smoke** — pretrained fire/smoke YOLO. Alerts with cooldown. Dedicated weights recommended; synthetic demo still visualizes flames if the checkpoint is missing.

**Store** — COCO `person` + IOU tracker. Line crossing increments in/out. Foot positions accumulate a heat map.

**Traffic** — COCO vehicles + tracker.

- *Wrong way*: velocity vs `allowed_direction`
- *Vehicles crossing*: stop-line crossings
- *Signal jump*: stop-line crossing while the light is classified **red** (YOLO `traffic light` crop, else `signal_roi`)

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | liveness + engine stats |
| `GET /api/cameras` | per-camera counts / alerts |
| `GET /api/events` | persisted events |
| `GET /api/heatmap/{id}` | normalized heat grid |
| `GET /api/stream/{id}.mjpeg` | live overlay |
| `WS /ws/live` | status + alerts |

SQLite events land in `data/events.db`.

## Tests

```bash
pytest -q
```

`--mock` skips YOLO weights (CI / CPU).

## Layout

```
vision-analytics/
  configs/           default engine + camera geometry
  dashboard/         operations UI
  src/vision_analytics/
    inference/       shared YOLO pool
    ingest/          RTSP + synthetic
    analytics/       fire, store, traffic
    tracking/        IOU tracker
    api.py           FastAPI
  scripts/           download + fine-tune
```
