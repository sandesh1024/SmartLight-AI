# backend/app/main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import asyncio
import os

from backend.core.signal_manager import SignalManager

app = FastAPI(title="Smart Traffic Control AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static video files ──────────────────────────────────────
VIDEOS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "videos")
)
if os.path.exists(VIDEOS_DIR):
    app.mount("/videos", StaticFiles(directory=VIDEOS_DIR), name="videos")
else:
    print(f"⚠ Videos folder not found: {VIDEOS_DIR}")

# ── Shared state ────────────────────────────────────────────
manager = SignalManager()
notifications_store: List[dict] = []   # ← shared, both apps read this


# ── Startup ─────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(manager.start())


# ── Health check ────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "Smart Traffic Control AI Running"}


# ── Signals ─────────────────────────────────────────────────
@app.get("/signals")
def get_signals():
    return manager.get_all_states()


class OverrideRequest(BaseModel):
    lane: str
    color: str
    duration: Optional[int] = 15

@app.post("/signals/{signal_id}/override")
def manual_override(signal_id: str, req: OverrideRequest):
    signal = manager.signals.get(signal_id)
    if not signal:
        return {"error": f"Signal {signal_id} not found"}
    signal.manual_override(lane=req.lane, color=req.color, duration=req.duration)
    return {"status": "ok", "signal": signal_id, "lane": req.lane, "color": req.color}


class EmergencyRequest(BaseModel):
    lane: str
    duration: Optional[int] = 30

@app.post("/signals/{signal_id}/emergency")
def emergency_override(signal_id: str, req: EmergencyRequest):
    signal = manager.signals.get(signal_id)
    if not signal:
        return {"error": f"Signal {signal_id} not found"}
    signal.manual_override(lane=req.lane, color="green", duration=req.duration)
    signal.emergency = True
    return {"status": "ok", "signal": signal_id, "emergency_lane": req.lane}


@app.post("/signals/{signal_id}/reset")
def reset_signal(signal_id: str):
    signal = manager.signals.get(signal_id)
    if not signal:
        return {"error": f"Signal {signal_id} not found"}
    signal.reset()
    manager.reinit_signal(signal_id)
    return {"status": "reset", "signal": signal_id}


@app.post("/signals/reset-all")
def reset_all():
    for signal in manager.signals.values():
        signal.reset()
    manager.reinit_all()
    return {"status": "all signals reset"}


@app.post("/signals/optimize")
def optimize():
    for signal in manager.signals.values():
        if signal._cycle_ready:
            signal._yolo_needed = {lane: True for lane in signal.lane_order}
    return {"status": "optimization triggered"}


# ── Notifications ────────────────────────────────────────────
# Admin sends → stored here → public app polls every 5s

class NotificationRequest(BaseModel):
    title: str
    message: str
    type: str       # info | warning | alert | emergency
    area: str       # all | bandra | worli | dadar | andheri | churchgate

@app.post("/notifications")
def send_notification(req: NotificationRequest):
    n = {
        "id":        int(datetime.now().timestamp() * 1000),
        "title":     req.title,
        "message":   req.message,
        "type":      req.type,
        "area":      req.area,
        "timestamp": datetime.now().strftime("%d %b %Y, %I:%M %p"),
    }
    notifications_store.insert(0, n)
    if len(notifications_store) > 50:
        notifications_store.pop()
    return {"status": "sent", "notification": n}

@app.get("/notifications")
def get_notifications():
    return notifications_store


# ── WebSocket ────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = manager.get_all_states()
            await websocket.send_json(data)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("Frontend disconnected")
    except Exception as e:
        print("WebSocket error:", e)