from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Optional
import json
import asyncio
from datetime import datetime, timedelta
import uuid
import os
from dotenv import load_dotenv
import qrcode
from io import BytesIO
import base64
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ai_dj import AIDJAgent

load_dotenv()

app = FastAPI(title="Jukebox AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast(self, message: dict, session_id: str):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

party_sessions = {}
song_requests = {}
voting_sessions = {}
user_wallets = {}
ai_dj_agents = {}

class PartySession(BaseModel):
    name: str
    artist_id: str

class SongRequest(BaseModel):
    song_name: str
    artist: str
    requester_name: str
    session_id: str
    tip_amount: float = 0.0

class Vote(BaseModel):
    session_id: str
    request_id: str

class TipRequest(BaseModel):
    session_id: str
    request_id: str
    amount: float

@app.post("/api/sessions/create")
async def create_session(session: PartySession):
    session_id = str(uuid.uuid4())[:8].upper()
    party_sessions[session_id] = {
        "id": session_id,
        "name": session.name,
        "artist_id": session.artist_id,
        "created_at": datetime.now().isoformat(),
        "active": True,
        "mode": "voting"
    }
    song_requests[session_id] = []
    ai_dj_agents[session_id] = AIDJAgent()
    
    qr_data = f"{os.getenv('REPLIT_DEV_DOMAIN', 'localhost:5000')}/join/{session_id}"
    img = qrcode.make(qr_data)
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    return {
        "session_id": session_id,
        "qr_code": qr_base64,
        "join_url": qr_data,
        "session": party_sessions[session_id]
    }

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    if session_id not in party_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return party_sessions[session_id]

@app.post("/api/requests/submit")
async def submit_request(request: SongRequest):
    if request.session_id not in party_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    request_id = str(uuid.uuid4())
    song_request = {
        "id": request_id,
        "song_name": request.song_name,
        "artist": request.artist,
        "requester_name": request.requester_name,
        "tip_amount": request.tip_amount,
        "votes": 0,
        "voters": [],
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    
    song_requests[request.session_id].append(song_request)
    
    await manager.broadcast({
        "type": "new_request",
        "request": song_request
    }, request.session_id)
    
    if len([r for r in song_requests[request.session_id] if r["status"] == "pending"]) >= 2:
        asyncio.create_task(start_voting_session(request.session_id))
    
    return {"request_id": request_id, "request": song_request}

async def start_voting_session(session_id: str):
    if session_id in voting_sessions and voting_sessions[session_id]["active"]:
        return
    
    pending_requests = [r for r in song_requests[session_id] if r["status"] == "pending"]
    if len(pending_requests) < 2:
        return
    
    voting_sessions[session_id] = {
        "active": True,
        "started_at": datetime.now(),
        "ends_at": datetime.now() + timedelta(seconds=60)
    }
    
    await manager.broadcast({
        "type": "voting_started",
        "duration": 60,
        "requests": pending_requests
    }, session_id)
    
    await asyncio.sleep(60)
    
    pending_requests = [r for r in song_requests[session_id] if r["status"] == "pending"]
    if pending_requests:
        winner = max(pending_requests, key=lambda x: x["votes"])
        winner["status"] = "queued"
        
        if session_id in ai_dj_agents:
            ai_dj_agents[session_id].add_to_playlist(winner)
        
        for req in pending_requests:
            if req["id"] != winner["id"]:
                req["status"] = "rejected"
        
        await manager.broadcast({
            "type": "voting_ended",
            "winner": winner,
            "all_requests": song_requests[session_id]
        }, session_id)
    
    voting_sessions[session_id]["active"] = False

@app.post("/api/requests/vote")
async def vote_for_request(vote: Vote):
    if vote.session_id not in party_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    request = next((r for r in song_requests[vote.session_id] if r["id"] == vote.request_id), None)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request["status"] != "pending":
        raise HTTPException(status_code=400, detail="Request is not open for voting")
    
    request["votes"] += 1
    
    await manager.broadcast({
        "type": "vote_update",
        "request_id": vote.request_id,
        "votes": request["votes"]
    }, vote.session_id)
    
    return {"success": True, "votes": request["votes"]}

@app.post("/api/requests/tip")
async def tip_request(tip: TipRequest):
    request = next((r for r in song_requests[tip.session_id] if r["id"] == tip.request_id), None)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    session = party_sessions.get(tip.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    artist_id = session["artist_id"]
    requester_id = request["requester_name"]
    
    if requester_id not in user_wallets:
        user_wallets[requester_id] = {"balance": 100.0, "transactions": []}
    
    if user_wallets[requester_id]["balance"] < tip.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    user_wallets[requester_id]["balance"] -= tip.amount
    user_wallets[requester_id]["transactions"].append({
        "type": "tip_sent",
        "amount": -tip.amount,
        "request_id": tip.request_id,
        "timestamp": datetime.now().isoformat()
    })
    
    if artist_id not in user_wallets:
        user_wallets[artist_id] = {"balance": 0.0, "transactions": []}
    
    request["tip_amount"] += tip.amount
    if "tip_escrow" not in request:
        request["tip_escrow"] = 0
    request["tip_escrow"] += tip.amount
    
    await manager.broadcast({
        "type": "tip_added",
        "request_id": tip.request_id,
        "total_tips": request["tip_amount"]
    }, tip.session_id)
    
    return {"success": True, "total_tips": request["tip_amount"]}

@app.post("/api/requests/{request_id}/complete")
async def complete_request(request_id: str, session_id: str):
    request = next((r for r in song_requests[session_id] if r["id"] == request_id), None)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request["status"] = "completed"
    
    session = party_sessions.get(session_id)
    if session and request.get("tip_escrow", 0) > 0:
        artist_id = session["artist_id"]
        if artist_id not in user_wallets:
            user_wallets[artist_id] = {"balance": 0.0, "transactions": []}
        
        tip_amount = request["tip_escrow"]
        user_wallets[artist_id]["balance"] += tip_amount
        user_wallets[artist_id]["transactions"].append({
            "type": "tip_received",
            "amount": tip_amount,
            "request_id": request_id,
            "from": request["requester_name"],
            "timestamp": datetime.now().isoformat()
        })
        request["tip_escrow"] = 0
    
    await manager.broadcast({
        "type": "request_completed",
        "request_id": request_id
    }, session_id)
    
    return {"success": True}

@app.post("/api/requests/{request_id}/skip")
async def skip_request(request_id: str, session_id: str):
    request = next((r for r in song_requests[session_id] if r["id"] == request_id), None)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request["status"] = "skipped"
    
    if request.get("tip_escrow", 0) > 0:
        requester_id = request["requester_name"]
        if requester_id in user_wallets:
            tip_amount = request["tip_escrow"]
            user_wallets[requester_id]["balance"] += tip_amount
            user_wallets[requester_id]["transactions"].append({
                "type": "tip_refund",
                "amount": tip_amount,
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            })
            request["tip_escrow"] = 0
    
    await manager.broadcast({
        "type": "request_skipped",
        "request_id": request_id
    }, session_id)
    
    return {"success": True}

@app.get("/api/requests/{session_id}")
async def get_requests(session_id: str):
    if session_id not in song_requests:
        return []
    return song_requests[session_id]

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)

@app.get("/api/wallet/{user_id}")
async def get_wallet(user_id: str):
    if user_id not in user_wallets:
        user_wallets[user_id] = {"balance": 100.0, "transactions": []}
    return user_wallets[user_id]

@app.post("/api/dj/{session_id}/enable")
async def enable_ai_dj(session_id: str):
    if session_id not in party_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    party_sessions[session_id]["mode"] = "ai_dj"
    
    pending_requests = [r for r in song_requests[session_id] if r["status"] == "pending"]
    for req in pending_requests:
        ai_dj_agents[session_id].add_to_playlist(req)
    
    await manager.broadcast({
        "type": "ai_dj_enabled",
        "playlist": ai_dj_agents[session_id].get_playlist_status()
    }, session_id)
    
    return {"success": True, "mode": "ai_dj"}

@app.get("/api/dj/{session_id}/playlist")
async def get_dj_playlist(session_id: str):
    if session_id not in ai_dj_agents:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return ai_dj_agents[session_id].get_playlist_status()

@app.post("/api/dj/{session_id}/next")
async def play_next_track(session_id: str):
    if session_id not in ai_dj_agents:
        raise HTTPException(status_code=404, detail="Session not found")
    
    next_track = ai_dj_agents[session_id].get_next_track()
    
    if next_track:
        await manager.broadcast({
            "type": "now_playing",
            "track": next_track
        }, session_id)
        
        return {"success": True, "track": next_track}
    
    return {"success": False, "message": "No more tracks"}

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles as BaseStaticFiles

class StaticFilesNoCache(BaseStaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

app.mount("/", StaticFilesNoCache(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
