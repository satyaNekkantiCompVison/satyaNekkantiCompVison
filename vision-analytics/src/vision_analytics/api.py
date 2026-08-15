from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from vision_analytics.pipeline import AnalyticsPipeline

DASHBOARD_DIR = Path(__file__).resolve().parents[2] / "dashboard"


class Hub:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def register(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self.clients.add(ws)

    async def unregister(self, ws: WebSocket) -> None:
        async with self._lock:
            self.clients.discard(ws)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        data = json.dumps(payload)
        async with self._lock:
            clients = list(self.clients)
        dead: list[WebSocket] = []
        for ws in clients:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.unregister(ws)


def create_app(pipeline: AnalyticsPipeline) -> FastAPI:
    hub = Hub()
    loop_holder: dict[str, asyncio.AbstractEventLoop] = {}

    def on_event(event: dict[str, Any]) -> None:
        loop = loop_holder.get("loop")
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(hub.broadcast({"kind": "event", "data": event}), loop)

    pipeline.subscribe(on_event)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        loop_holder["loop"] = asyncio.get_running_loop()
        yield

    app = FastAPI(title="Vision Analytics", version="0.1.0", lifespan=lifespan)

    if DASHBOARD_DIR.exists():
        app.mount("/static", StaticFiles(directory=DASHBOARD_DIR), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        index_path = DASHBOARD_DIR / "index.html"
        if not index_path.exists():
            raise HTTPException(404, "dashboard not packaged")
        return FileResponse(index_path)

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {"ok": True, "engine": pipeline.engine_stats()}

    @app.get("/api/engine")
    async def engine() -> dict[str, Any]:
        return pipeline.engine_stats()

    @app.get("/api/cameras")
    async def cameras() -> list[dict[str, Any]]:
        return pipeline.camera_status()

    @app.get("/api/events")
    async def events(camera_id: str | None = None, type: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        return pipeline.store.list_events(camera_id=camera_id, type_=type, limit=limit)

    @app.get("/api/analytics")
    async def analytics() -> dict[str, Any]:
        return pipeline.analytics_bundle()

    @app.get("/api/insights")
    async def insights() -> dict[str, Any]:
        bundle = pipeline.analytics_bundle()
        return {"insights": bundle["insights"], "summary": bundle["summary"]}

    @app.get("/api/heatmap/{camera_id}")
    async def heatmap(camera_id: str) -> JSONResponse:
        rt = pipeline.cameras.get(camera_id)
        if not rt or not rt.store:
            raise HTTPException(404, "heatmap not available")
        return JSONResponse({"camera_id": camera_id, "grid": rt.store.heatmap_normalized(), **rt.store.snapshot()})

    @app.get("/api/heatmap/{camera_id}.jpg")
    async def heatmap_jpg(camera_id: str) -> Response:
        data = pipeline.heatmap_jpeg(camera_id)
        if not data:
            raise HTTPException(404, "heatmap not available")
        return Response(content=data, media_type="image/jpeg")

    @app.get("/api/snapshot/{camera_id}.jpg")
    async def snapshot(camera_id: str) -> Response:
        data = pipeline.overlay_jpeg(camera_id)
        if not data:
            raise HTTPException(404, "no frame yet")
        return Response(content=data, media_type="image/jpeg")

    @app.get("/api/stream/{camera_id}.mjpeg")
    async def mjpeg(camera_id: str) -> StreamingResponse:
        if camera_id not in pipeline.cameras:
            raise HTTPException(404, "unknown camera")

        async def gen():
            while True:
                data = pipeline.overlay_jpeg(camera_id, quality=55)
                if data:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + data + b"\r\n"
                await asyncio.sleep(0.07)

        return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.websocket("/ws/live")
    async def ws_live(ws: WebSocket) -> None:
        await hub.register(ws)
        try:
            bundle = pipeline.analytics_bundle()
            await ws.send_text(
                json.dumps(
                    {
                        "kind": "hello",
                        "cameras": bundle["cameras"],
                        "engine": pipeline.engine_stats(),
                        "insights": bundle["insights"],
                        "summary": bundle["summary"],
                    }
                )
            )
            while True:
                await asyncio.sleep(1.0)
                bundle = pipeline.analytics_bundle()
                await ws.send_text(
                    json.dumps(
                        {
                            "kind": "status",
                            "cameras": bundle["cameras"],
                            "engine": pipeline.engine_stats(),
                            "insights": bundle["insights"],
                            "summary": bundle["summary"],
                        }
                    )
                )
        except WebSocketDisconnect:
            pass
        finally:
            await hub.unregister(ws)

    return app
