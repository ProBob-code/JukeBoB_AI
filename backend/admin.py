"""
Admin Dashboard Backend
Password-protected admin panel for managing WTPT events and Games
"""

import hashlib
import secrets
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import uuid

# Data storage paths
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
EVENTS_FILE = DATA_DIR / "admin_events.json"
GAMES_FILE = DATA_DIR / "admin_games.json"
SESSIONS_FILE = DATA_DIR / "admin_sessions.json"

# Admin credentials come from the environment. ADMIN_USERNAME/ADMIN_PASSWORD
# override the development default (admin / jukebob2026) and should always be
# set in production.
_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "jukebob2026")
ADMIN_CREDENTIALS = {
    _ADMIN_USERNAME: hashlib.sha256(_ADMIN_PASSWORD.encode()).hexdigest()
}

# Sessions expire after this many hours of age.
SESSION_TTL_HOURS = int(os.getenv("ADMIN_SESSION_TTL_HOURS", "24"))

# Active sessions
active_sessions: Dict[str, dict] = {}


def load_sessions():
    """Load sessions from file"""
    global active_sessions
    if SESSIONS_FILE.exists():
        try:
            with open(SESSIONS_FILE, 'r') as f:
                active_sessions = json.load(f)
        except:
            active_sessions = {}


def save_sessions():
    """Save sessions to file"""
    with open(SESSIONS_FILE, 'w') as f:
        json.dump(active_sessions, f)


def verify_admin(username: str, password: str) -> Optional[str]:
    """Verify admin credentials and return session token"""
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    if username in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[username] == password_hash:
        # Generate session token
        token = secrets.token_hex(32)
        active_sessions[token] = {
            "username": username,
            "created_at": datetime.now().isoformat(),
        }
        save_sessions()
        return token
    return None


def verify_session(token: str) -> bool:
    """Verify if session token is valid and not expired"""
    load_sessions()
    session = active_sessions.get(token)
    if not session:
        return False
    try:
        created = datetime.fromisoformat(session["created_at"])
        if datetime.now() - created > timedelta(hours=SESSION_TTL_HOURS):
            del active_sessions[token]
            save_sessions()
            return False
    except (KeyError, ValueError):
        return False
    return True


def logout(token: str):
    """Invalidate session token"""
    if token in active_sessions:
        del active_sessions[token]
        save_sessions()


# ============== WTPT EVENTS ==============

def load_events() -> List[Dict]:
    """Load events from file"""
    if EVENTS_FILE.exists():
        try:
            with open(EVENTS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []


def save_events(events: List[Dict]):
    """Save events to file"""
    with open(EVENTS_FILE, 'w') as f:
        json.dump(events, f, indent=2)


def create_event(
    title: str,
    link: str,
    image_url: str,
    tag: str,  # "available", "filling_soon", "sold_out"
    event_datetime: str,
    venue: str,
    city: str,
    price: str
) -> Dict:
    """Create a new WTPT event"""
    events = load_events()
    
    event = {
        "id": str(uuid.uuid4())[:8],
        "title": title,
        "link": link,
        "image_url": image_url if image_url else "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400",
        "tag": tag,
        "event_datetime": event_datetime,
        "venue": venue,
        "city": city.lower(),
        "price": price,
        "approved": False,
        "created_at": datetime.now().isoformat(),
    }
    
    events.append(event)
    save_events(events)
    return event


def get_all_events() -> List[Dict]:
    """Get all events for admin dashboard"""
    events = load_events()
    # Clean up expired events (but keep them visible in admin)
    now = datetime.now()
    for event in events:
        try:
            event_dt = datetime.fromisoformat(event["event_datetime"])
            event["expired"] = event_dt < now
        except:
            event["expired"] = False
    return events


def get_approved_events(city: Optional[str] = None) -> List[Dict]:
    """Get only approved and non-expired events for live app"""
    events = load_events()
    now = datetime.now()
    
    approved = []
    for event in events:
        if not event.get("approved", False):
            continue
        
        # Check if expired
        try:
            event_dt = datetime.fromisoformat(event["event_datetime"])
            if event_dt < now:
                continue  # Skip expired events
        except:
            pass
        
        # Filter by city if specified
        if city and event.get("city", "").lower() != city.lower():
            continue
        
        approved.append(event)
    
    return approved


def update_event(event_id: str, updates: Dict) -> Optional[Dict]:
    """Update an event"""
    events = load_events()
    
    for i, event in enumerate(events):
        if event["id"] == event_id:
            events[i].update(updates)
            save_events(events)
            return events[i]
    
    return None


def approve_event(event_id: str, approved: bool = True) -> Optional[Dict]:
    """Approve or unapprove an event"""
    return update_event(event_id, {"approved": approved})


def delete_event(event_id: str) -> bool:
    """Delete an event"""
    events = load_events()
    initial_count = len(events)
    events = [e for e in events if e["id"] != event_id]
    
    if len(events) < initial_count:
        save_events(events)
        return True
    return False


# ============== GAMES ==============

def load_games() -> List[Dict]:
    """Load games from file"""
    if GAMES_FILE.exists():
        try:
            with open(GAMES_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []


def save_games(games: List[Dict]):
    """Save games to file"""
    with open(GAMES_FILE, 'w') as f:
        json.dump(games, f, indent=2)


def create_game(
    name: str,
    description: str,
    image_url: str,
    game_type: str  # "trivia", "puzzle", "multiplayer", etc.
) -> Dict:
    """Create a new game entry"""
    games = load_games()
    
    game = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "description": description,
        "image_url": image_url if image_url else "https://images.unsplash.com/photo-1511512578047-dfb367046420?w=400",
        "game_type": game_type,
        "approved": False,
        "created_at": datetime.now().isoformat(),
    }
    
    games.append(game)
    save_games(games)
    return game


def get_all_games() -> List[Dict]:
    """Get all games for admin dashboard"""
    return load_games()


def get_approved_games() -> List[Dict]:
    """Get only approved games for live app"""
    games = load_games()
    return [g for g in games if g.get("approved", False)]


def approve_game(game_id: str, approved: bool = True) -> Optional[Dict]:
    """Approve or unapprove a game"""
    games = load_games()
    
    for i, game in enumerate(games):
        if game["id"] == game_id:
            games[i]["approved"] = approved
            save_games(games)
            return games[i]
    
    return None


def delete_game(game_id: str) -> bool:
    """Delete a game"""
    games = load_games()
    initial_count = len(games)
    games = [g for g in games if g["id"] != game_id]
    
    if len(games) < initial_count:
        save_games(games)
        return True
    return False


# Initialize on import
load_sessions()
