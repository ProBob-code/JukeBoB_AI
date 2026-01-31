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
import hashlib
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
game_rooms = {}
payment_transactions = {}
app_revenue = {"total": 0.0, "transactions": []}

class PartySession(BaseModel):
    name: str
    artist_id: str
    password: str

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

class GameRoom(BaseModel):
    game_type: str
    player_name: str
    password: str

class GameMove(BaseModel):
    room_code: str
    player_name: str
    move: int

class EmojiReaction(BaseModel):
    room_code: str
    player_name: str
    emoji: str

class PaymentCheckout(BaseModel):
    session_id: str
    payment_method: str  # "upi" or "gpay"
    upi_id: Optional[str] = None

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@app.post("/api/sessions/create")
async def create_session(session: PartySession):
    session_id = str(uuid.uuid4())[:8].upper()
    party_sessions[session_id] = {
        "id": session_id,
        "name": session.name,
        "artist_id": session.artist_id,
        "password_hash": hash_password(session.password),
        "created_at": datetime.now().isoformat(),
        "active": True,
        "mode": "voting",
        "participants": [],
        "tips_by_member": {}
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

class JoinSession(BaseModel):
    guest_name: str
    password: str

class ResumeSession(BaseModel):
    password: str

@app.post("/api/sessions/{session_id}/join")
async def join_session(session_id: str, join_data: JoinSession):
    if session_id not in party_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = party_sessions[session_id]
    if hash_password(join_data.password) != session["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid password")
    
    if join_data.guest_name not in session["participants"]:
        session["participants"].append(join_data.guest_name)
    
    await manager.broadcast({
        "type": "user_joined",
        "user": join_data.guest_name
    }, session_id)
    
    return session

@app.post("/api/sessions/{session_id}/resume")
async def resume_session(session_id: str, resume_data: ResumeSession):
    if session_id not in party_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = party_sessions[session_id]
    if hash_password(resume_data.password) != session["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid password")
    
    # Generate QR code again
    qr_data = f"{os.getenv('REPLIT_DEV_DOMAIN', 'localhost:5000')}/join/{session_id}"
    img = qrcode.make(qr_data)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    # Determine user role based on artist_id
    user_role = {"name": session["artist_id"], "role": "host"} if resume_data.password else {"name": "Guest", "role": "guest"}
    
    return {
        "session": session,
        "qr_code": qr_base64,
        "user_role": user_role
    }

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
        "status": "queued",  # Changed from "pending" to "queued" - songs go directly to queue
        "created_at": datetime.now().isoformat()
    }
    
    # Track tips by member
    session = party_sessions[request.session_id]
    if request.requester_name not in session["tips_by_member"]:
        session["tips_by_member"][request.requester_name] = 0
    session["tips_by_member"][request.requester_name] += request.tip_amount
    
    song_requests[request.session_id].append(song_request)
    
    # Broadcast to all connected clients
    await manager.broadcast({
        "type": "new_request",
        "request": song_request,
        "queue": song_requests[request.session_id]
    }, request.session_id)
    
    # Removed voting system - songs go directly to queue
    
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
    
    # Segregate VIP and Regular queue songs
    requests = song_requests[session_id]
    queued_songs = [r for r in requests if r["status"] == "queued"]
    
    # VIP songs: tips >= ₹10, sorted by tip amount (highest first)
    vip_songs = sorted(
        [r for r in queued_songs if r.get("tip_amount", 0) >= 10],
        key=lambda x: x.get("tip_amount", 0),
        reverse=True
    )
    
    # Regular songs: tips < ₹10, kept in submission order (by created_at)
    regular_songs = [r for r in queued_songs if r.get("tip_amount", 0) < 10]
    # Regular songs maintain their submission order (no sorting needed since they're already in order)
    
    # Combine: VIP songs first, then Regular songs
    all_queued = vip_songs + regular_songs
    
    # Get other statuses (completed, skipped, etc.)
    other = [r for r in requests if r["status"] != "queued"]
    
    # Return all requests with VIP prioritized in queue
    return all_queued + other

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

@app.post("/api/checkout/process")
async def process_checkout(checkout: PaymentCheckout):
    """Process UPI/GPay checkout with 5% app fee"""
    if checkout.session_id not in party_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = party_sessions[checkout.session_id]
    artist_earnings = session.get("artist_earnings", 0)
    
    if artist_earnings <= 0:
        return {"success": False, "message": "No earnings to checkout"}
    
    # Calculate 5% app fee
    app_fee = artist_earnings * 0.05
    net_amount = artist_earnings - app_fee
    
    # Create payment transaction
    transaction_id = str(uuid.uuid4())[:8].upper()
    payment_transactions[transaction_id] = {
        "id": transaction_id,
        "session_id": checkout.session_id,
        "gross_amount": artist_earnings,
        "app_fee": app_fee,
        "net_amount": net_amount,
        "payment_method": checkout.payment_method,
        "upi_id": checkout.upi_id,
        "status": "processing",
        "created_at": datetime.now().isoformat()
    }
    
    # Simulate payment processing (in production, this would call UPI gateway API)
    await asyncio.sleep(2)  # Simulate processing delay
    
    # Mark transaction as completed
    payment_transactions[transaction_id]["status"] = "completed"
    
    # Record app revenue
    app_revenue["total"] += app_fee
    app_revenue["transactions"].append({
        "transaction_id": transaction_id,
        "fee": app_fee,
        "timestamp": datetime.now().isoformat()
    })
    
    # Clear artist earnings after successful checkout
    session["artist_earnings"] = 0
    
    # Broadcast payment success
    await manager.broadcast({
        "type": "payment_processed",
        "transaction": payment_transactions[transaction_id]
    }, checkout.session_id)
    
    return {
        "success": True,
        "transaction_id": transaction_id,
        "gross_amount": artist_earnings,
        "app_fee": app_fee,
        "net_amount": net_amount,
        "payment_method": checkout.payment_method,
        "message": f"Payment of ₹{net_amount:.2f} processed successfully"
    }

@app.get("/api/transactions/{transaction_id}")
async def get_transaction(transaction_id: str):
    """Get transaction details"""
    if transaction_id not in payment_transactions:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return payment_transactions[transaction_id]

@app.get("/api/app/revenue")
async def get_app_revenue():
    """Get app revenue statistics"""
    return app_revenue

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

@app.post("/api/games/create")
async def create_game_room(room: GameRoom):
    room_code = str(uuid.uuid4())[:6].upper()
    game_rooms[room_code] = {
        "code": room_code,
        "type": room.game_type,
        "player1": room.player_name,
        "player2": None,
        "password_hash": hash_password(room.password),
        "board": [None] * 9,
        "current_turn": "X",
        "status": "waiting",
        "created_at": datetime.now().isoformat(),
        # New fields for scoreboard and leaderboard
        "scores": {"X": 0, "O": 0},
        "games_played": 0,
        "starting_player": "X",  # Track who starts each round
        "leaderboard": {
            room.player_name: {
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "games": 0,
                "streak": 0,
                "max_streak": 0
            }
        },
        "restart_requests": [],  # Track restart requests from players
        "round_history": []  # Track history of each round
    }
    return {"room_code": room_code, "room": game_rooms[room_code]}

class JoinGameRoom(BaseModel):
    player_name: str
    password: str

@app.post("/api/games/join/{room_code}")
async def join_game_room(room_code: str, join_data: JoinGameRoom):
    if room_code not in game_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = game_rooms[room_code]
    if hash_password(join_data.password) != room["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid password")
    
    if room["player2"]:
        raise HTTPException(status_code=400, detail="Room is full")
    
    room["player2"] = join_data.player_name
    room["status"] = "playing"
    
    # Initialize leaderboard for player2
    if join_data.player_name not in room["leaderboard"]:
        room["leaderboard"][join_data.player_name] = {
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "games": 0,
            "streak": 0,
            "max_streak": 0
        }
    
    await manager.broadcast({
        "type": "player_joined",
        "room": room
    }, room_code)
    
    return {"success": True, "room": room}

@app.get("/api/games/{room_code}")
async def get_game_room(room_code: str):
    if room_code not in game_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return game_rooms[room_code]

@app.post("/api/games/move")
async def make_game_move(move: GameMove):
    if move.room_code not in game_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = game_rooms[move.room_code]
    
    if room["board"][move.move] is not None:
        raise HTTPException(status_code=400, detail="Invalid move")
    
    # Determine player symbol
    symbol = "X" if room["player1"] == move.player_name else "O"
    
    if room["current_turn"] != symbol:
        raise HTTPException(status_code=400, detail="Not your turn")
    
    room["board"][move.move] = symbol
    room["current_turn"] = "O" if symbol == "X" else "X"
    
    # Check for winner
    winner = check_tictactoe_winner(room["board"])
    if winner:
        room["status"] = "finished"
        room["winner"] = winner
        
        # Update scores
        room["scores"][winner] += 1
        room["games_played"] += 1
        
        # Update leaderboard
        winner_name = room["player1"] if winner == "X" else room["player2"]
        loser_name = room["player2"] if winner == "X" else room["player1"]
        
        if winner_name and winner_name in room["leaderboard"]:
            room["leaderboard"][winner_name]["wins"] += 1
            room["leaderboard"][winner_name]["games"] += 1
            room["leaderboard"][winner_name]["streak"] += 1
            if room["leaderboard"][winner_name]["streak"] > room["leaderboard"][winner_name]["max_streak"]:
                room["leaderboard"][winner_name]["max_streak"] = room["leaderboard"][winner_name]["streak"]
        
        if loser_name and loser_name in room["leaderboard"]:
            room["leaderboard"][loser_name]["losses"] += 1
            room["leaderboard"][loser_name]["games"] += 1
            room["leaderboard"][loser_name]["streak"] = 0
        
        # Record round history
        room["round_history"].append({
            "round": room["games_played"],
            "winner": winner_name,
            "moves": len([m for m in room["board"] if m is not None]),
            "timestamp": datetime.now().isoformat()
        })
        
    elif all(cell is not None for cell in room["board"]):
        room["status"] = "draw"
        room["games_played"] += 1
        
        # Update leaderboard for draws
        for player_name in [room["player1"], room["player2"]]:
            if player_name and player_name in room["leaderboard"]:
                room["leaderboard"][player_name]["draws"] += 1
                room["leaderboard"][player_name]["games"] += 1
                room["leaderboard"][player_name]["streak"] = 0
        
        # Record round history
        room["round_history"].append({
            "round": room["games_played"],
            "winner": "draw",
            "moves": 9,
            "timestamp": datetime.now().isoformat()
        })
    
    await manager.broadcast({
        "type": "game_move",
        "room": room
    }, move.room_code)
    
    return {"success": True, "room": room}

def check_tictactoe_winner(board):
    wins = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],
        [0, 3, 6], [1, 4, 7], [2, 5, 8],
        [0, 4, 8], [2, 4, 6]
    ]
    
    for combo in wins:
        a, b, c = combo
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None

@app.post("/api/games/emoji")
async def send_emoji_reaction(reaction: EmojiReaction):
    if reaction.room_code not in game_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Broadcast emoji to all players in the room
    await manager.broadcast({
        "type": "emoji_reaction",
        "player_name": reaction.player_name,
        "emoji": reaction.emoji
    }, reaction.room_code)
    
    return {"success": True}

class RestartRequest(BaseModel):
    room_code: str
    player_name: str
    
@app.post("/api/games/restart")
async def restart_game(restart: RestartRequest):
    if restart.room_code not in game_rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = game_rooms[restart.room_code]
    
    # Check if player is in the room
    if restart.player_name not in [room["player1"], room["player2"]]:
        raise HTTPException(status_code=400, detail="Player not in room")
    
    # Add player's restart request if not already present
    if restart.player_name not in room["restart_requests"]:
        room["restart_requests"].append(restart.player_name)
    
    # Check if both players requested restart
    both_players_requested = len(room["restart_requests"]) >= 2
    is_host = restart.player_name == room["player1"]
    
    # Restart if both players agreed or if host requests (host can force restart)
    if both_players_requested or is_host:
        # Clear the board
        room["board"] = [None] * 9
        
        # Alternate starting player
        room["starting_player"] = "O" if room["starting_player"] == "X" else "X"
        room["current_turn"] = room["starting_player"]
        
        # Reset game status
        room["status"] = "playing"
        if "winner" in room:
            del room["winner"]
        
        # Clear restart requests
        room["restart_requests"] = []
        
        # Broadcast game restart
        await manager.broadcast({
            "type": "game_restarted",
            "room": room,
            "starting_player": room["starting_player"]
        }, restart.room_code)
        
        return {"success": True, "restarted": True, "room": room}
    else:
        # Notify that restart is pending
        await manager.broadcast({
            "type": "restart_requested",
            "requesting_player": restart.player_name,
            "restart_requests": room["restart_requests"]
        }, restart.room_code)
        
        return {"success": True, "restarted": False, "pending": True}

# ============== WTPT (Where's the Party Tonight) ==============

from wtpt import scraper, create_booking, get_bookings, get_booking, generate_invoice_html, CITIES
from fastapi.responses import HTMLResponse

class WTPTBooking(BaseModel):
    event_id: str
    event_title: str
    platform: str
    platform_booking_id: str
    user_name: str
    user_email: str
    user_phone: str
    tickets: int = 1
    total_amount: float = 0
    event_date: str
    venue: str

@app.get("/api/wtpt/events")
async def get_wtpt_events(city: str = "mumbai", category: Optional[str] = None):
    """Get music events from all platforms"""
    try:
        events = scraper.get_all_events(city, category)
        
        # If no events found (scraping may have failed), return mock data
        if not events:
            events = scraper.get_mock_events(city)
        
        return {
            "success": True,
            "city": city,
            "category": category,
            "count": len(events),
            "events": events
        }
    except Exception as e:
        # Fallback to mock data
        return {
            "success": True,
            "city": city,
            "category": category,
            "count": 4,
            "events": scraper.get_mock_events(city),
            "note": "Using sample data"
        }

@app.get("/api/wtpt/cities")
async def get_wtpt_cities():
    """Get list of supported cities"""
    return {
        "cities": list(CITIES.keys())
    }

@app.post("/api/wtpt/bookings")
async def create_wtpt_booking(booking: WTPTBooking):
    """Record a booking made through external platform"""
    booking_record = create_booking(booking.dict())
    return {
        "success": True,
        "booking": booking_record
    }

@app.get("/api/wtpt/bookings")
async def get_wtpt_bookings(email: Optional[str] = None):
    """Get all bookings or filter by email"""
    bookings_list = get_bookings(email)
    return {
        "success": True,
        "count": len(bookings_list),
        "bookings": bookings_list
    }

@app.get("/api/wtpt/bookings/{booking_id}")
async def get_wtpt_booking(booking_id: str):
    """Get a specific booking"""
    booking = get_booking(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@app.get("/api/wtpt/invoice/{booking_id}", response_class=HTMLResponse)
async def get_wtpt_invoice(booking_id: str):
    """Generate HTML invoice for a booking"""
    invoice_html = generate_invoice_html(booking_id)
    if not invoice_html:
        raise HTTPException(status_code=404, detail="Booking not found")
    return HTMLResponse(content=invoice_html)

# ============================================
# TRACKER API ENDPOINTS
# ============================================
from tracker import (
    create_tracker, get_all_trackers, get_tracker, 
    update_tracker_item, delete_tracker, create_demo_tracker
)
from fastapi import UploadFile, File

@app.post("/api/tracker/upload")
async def upload_tracker_file(file: UploadFile = File(...)):
    """Upload a file and create a tracker from it"""
    try:
        content = await file.read()
        tracker = create_tracker(content, file.filename, file.content_type)
        return {
            "success": True,
            "tracker": tracker
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/api/tracker/list")
async def list_trackers():
    """Get all trackers"""
    trackers = get_all_trackers()
    return {
        "success": True,
        "count": len(trackers),
        "trackers": trackers
    }

@app.get("/api/tracker/{tracker_id}")
async def get_single_tracker(tracker_id: str):
    """Get a specific tracker"""
    tracker = get_tracker(tracker_id)
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker not found")
    return tracker

class TrackerItemUpdate(BaseModel):
    item_id: str
    completed: bool

@app.put("/api/tracker/{tracker_id}/item")
async def update_item(tracker_id: str, update: TrackerItemUpdate):
    """Update a tracker item's completion status"""
    tracker = update_tracker_item(tracker_id, update.item_id, update.completed)
    if not tracker:
        raise HTTPException(status_code=404, detail="Tracker or item not found")
    return {"success": True, "tracker": tracker}

@app.delete("/api/tracker/{tracker_id}")
async def remove_tracker(tracker_id: str):
    """Delete a tracker"""
    success = delete_tracker(tracker_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tracker not found")
    return {"success": True}

@app.post("/api/tracker/demo")
async def create_demo():
    """Create a demo tracker with psychology theorists"""
    tracker = create_demo_tracker()
    return {"success": True, "tracker": tracker}

# ============== ADMIN DASHBOARD ==============
from admin import (
    verify_admin, verify_session, logout,
    create_event, get_all_events, get_approved_events, update_event, approve_event, delete_event,
    create_game as admin_create_game, get_all_games as admin_get_all_games, get_approved_games, approve_game, delete_game as admin_delete_game
)

class AdminLogin(BaseModel):
    username: str
    password: str

class AdminEventCreate(BaseModel):
    title: str
    link: str
    image_url: str = ""
    tag: str = "available"  # available, filling_soon, sold_out
    event_datetime: str
    venue: str
    city: str
    price: str

class AdminEventUpdate(BaseModel):
    title: Optional[str] = None
    link: Optional[str] = None
    image_url: Optional[str] = None
    tag: Optional[str] = None
    event_datetime: Optional[str] = None
    venue: Optional[str] = None
    city: Optional[str] = None
    price: Optional[str] = None
    approved: Optional[bool] = None

class AdminGameCreate(BaseModel):
    name: str
    description: str
    image_url: str = ""
    game_type: str = "trivia"

@app.post("/api/admin/login")
async def admin_login(login: AdminLogin):
    """Admin login - returns session token"""
    token = verify_admin(login.username, login.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"success": True, "token": token}

@app.post("/api/admin/logout")
async def admin_logout(token: str):
    """Admin logout - invalidates session"""
    logout(token)
    return {"success": True}

@app.get("/api/admin/verify")
async def admin_verify(token: str):
    """Verify admin session"""
    if not verify_session(token):
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return {"valid": True}

# WTPT Event Management
@app.post("/api/admin/events")
async def admin_create_event(event: AdminEventCreate, token: str):
    """Create a new WTPT event"""
    if not verify_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    new_event = create_event(
        title=event.title,
        link=event.link,
        image_url=event.image_url,
        tag=event.tag,
        event_datetime=event.event_datetime,
        venue=event.venue,
        city=event.city,
        price=event.price
    )
    return {"success": True, "event": new_event}

@app.get("/api/admin/events")
async def admin_list_events(token: str):
    """Get all events for admin dashboard"""
    if not verify_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"events": get_all_events()}

@app.put("/api/admin/events/{event_id}")
async def admin_update_event(event_id: str, event: AdminEventUpdate, token: str):
    """Update an event"""
    if not verify_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    updates = {k: v for k, v in event.dict().items() if v is not None}
    updated = update_event(event_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"success": True, "event": updated}

@app.post("/api/admin/events/{event_id}/approve")
async def admin_approve_event(event_id: str, token: str, approved: bool = True):
    """Approve or unapprove an event"""
    if not verify_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    event = approve_event(event_id, approved)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"success": True, "event": event}

@app.delete("/api/admin/events/{event_id}")
async def admin_remove_event(event_id: str, token: str):
    """Delete an event"""
    if not verify_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    success = delete_event(event_id)
    if not success:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"success": True}

# Game Management
@app.post("/api/admin/games")
async def admin_add_game(game: AdminGameCreate, token: str):
    """Add a new game"""
    if not verify_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    new_game = admin_create_game(
        name=game.name,
        description=game.description,
        image_url=game.image_url,
        game_type=game.game_type
    )
    return {"success": True, "game": new_game}

@app.get("/api/admin/games")
async def admin_list_games(token: str):
    """Get all games for admin dashboard"""
    if not verify_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"games": admin_get_all_games()}

@app.post("/api/admin/games/{game_id}/approve")
async def admin_approve_game(game_id: str, token: str, approved: bool = True):
    """Approve or unapprove a game"""
    if not verify_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    game = approve_game(game_id, approved)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return {"success": True, "game": game}

@app.delete("/api/admin/games/{game_id}")
async def admin_remove_game(game_id: str, token: str):
    """Delete a game"""
    if not verify_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    success = admin_delete_game(game_id)
    if not success:
        raise HTTPException(status_code=404, detail="Game not found")
    return {"success": True}

# Public endpoints for approved content
@app.get("/api/wtpt/approved-events")
async def get_wtpt_approved_events(city: Optional[str] = None):
    """Get approved and non-expired events for the live app"""
    return {"events": get_approved_events(city)}

@app.get("/api/games/approved")
async def get_games_approved():
    """Get approved games for the live app"""
    return {"games": get_approved_games()}

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles as BaseStaticFiles

class StaticFilesNoCache(BaseStaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

import pathlib
BACKEND_DIR = pathlib.Path(__file__).parent.resolve()
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
app.mount("/", StaticFilesNoCache(directory=str(FRONTEND_DIR), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
