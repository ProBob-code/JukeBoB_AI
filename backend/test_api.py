"""
End-to-end API tests for JukeBoB.

Run from the backend/ directory:
    pytest -q

These use a temporary data directory so they never touch real persisted state.
"""
import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Isolate persistence into a temp dir and reload the app fresh each test.
    monkeypatch.setenv("ADMIN_PASSWORD", "test-admin-pw")
    monkeypatch.chdir(tmp_path)
    import main
    importlib.reload(main)
    # Redirect the state file into the temp dir
    main.STATE_FILE = tmp_path / "state.json"
    main.party_sessions.clear()
    main.song_requests.clear()
    main.game_rooms.clear()
    main.user_wallets.clear()
    main.payment_transactions.clear()
    main.app_revenue.update({"total": 0.0, "transactions": []})
    return TestClient(main.app)


def create_session(client, password="secret1"):
    r = client.post("/api/sessions/create", json={
        "name": "Party", "artist_id": "Bob", "password": password})
    assert r.status_code == 200
    return r.json()


# ---------- Jukebox ----------

def test_create_session_hides_password_hash(client):
    data = create_session(client)
    assert "host_token" in data
    assert "password_hash" not in data["session"]


def test_join_wrong_password_rejected(client):
    data = create_session(client)
    sid = data["session_id"]
    r = client.post(f"/api/sessions/{sid}/join",
                    json={"guest_name": "Eve", "password": "wrong"})
    assert r.status_code == 401


def test_vip_queue_ordering(client):
    data = create_session(client)
    sid = data["session_id"]
    client.post("/api/requests/submit", json={
        "song_name": "Regular", "artist": "A", "requester_name": "Al",
        "session_id": sid, "tip_amount": 5})
    client.post("/api/requests/submit", json={
        "song_name": "VIP", "artist": "B", "requester_name": "Al",
        "session_id": sid, "tip_amount": 50})
    queue = client.get(f"/api/requests/{sid}").json()
    assert queue[0]["song_name"] == "VIP"  # VIP first


def test_queue_cap_enforced(client):
    data = create_session(client)
    sid = data["session_id"]
    for i in range(main_max := 10):
        r = client.post("/api/requests/submit", json={
            "song_name": f"S{i}", "artist": "A", "requester_name": "Al",
            "session_id": sid, "tip_amount": 1})
        assert r.status_code == 200
    r = client.post("/api/requests/submit", json={
        "song_name": "overflow", "artist": "A", "requester_name": "Al",
        "session_id": sid, "tip_amount": 1})
    assert r.status_code == 400


def test_complete_requires_host_token(client):
    data = create_session(client)
    sid = data["session_id"]
    rid = client.post("/api/requests/submit", json={
        "song_name": "S", "artist": "A", "requester_name": "Al",
        "session_id": sid, "tip_amount": 20}).json()["request_id"]
    # Without token -> forbidden
    assert client.post(f"/api/requests/{rid}/complete?session_id={sid}").status_code == 403
    # With wrong token -> forbidden
    assert client.post(
        f"/api/requests/{rid}/complete?session_id={sid}&host_token=nope").status_code == 403


def test_checkout_pays_out_completed_tips(client):
    """The core money bug: earnings must accrue on completion and pay out."""
    data = create_session(client)
    sid, token = data["session_id"], data["host_token"]
    rid = client.post("/api/requests/submit", json={
        "song_name": "S", "artist": "A", "requester_name": "Al",
        "session_id": sid, "tip_amount": 100}).json()["request_id"]
    client.post(f"/api/requests/{rid}/complete?session_id={sid}&host_token={token}")
    r = client.post("/api/checkout/process", json={
        "session_id": sid, "payment_method": "upi", "upi_id": "bob@upi",
        "host_token": token}).json()
    assert r["success"] is True
    assert r["gross_amount"] == 100
    assert round(r["app_fee"], 2) == 5.0
    assert round(r["net_amount"], 2) == 95.0


def test_checkout_requires_host_token(client):
    data = create_session(client)
    sid = data["session_id"]
    r = client.post("/api/checkout/process", json={
        "session_id": sid, "payment_method": "upi", "host_token": "bad"})
    assert r.status_code == 403


# ---------- Games ----------

def create_game(client):
    r = client.post("/api/games/create", json={
        "game_type": "tictactoe", "player_name": "P1", "password": "pw"}).json()
    j = client.post(f"/api/games/join/{r['room_code']}", json={
        "player_name": "P2", "password": "pw"}).json()
    return r["room_code"], r["player_token"], j["player_token"]


def test_game_move_requires_valid_token(client):
    code, p1_token, p2_token = create_game(client)
    # Impersonation attempt: no token
    assert client.post("/api/games/move", json={
        "room_code": code, "player_name": "P1", "move": 0}).status_code == 403
    # Impersonation attempt: wrong token
    assert client.post("/api/games/move", json={
        "room_code": code, "player_name": "P1", "move": 0,
        "player_token": "forged"}).status_code == 403
    # Legit move
    assert client.post("/api/games/move", json={
        "room_code": code, "player_name": "P1", "move": 0,
        "player_token": p1_token}).status_code == 200


def test_game_response_hides_tokens(client):
    code, _, _ = create_game(client)
    room = client.get(f"/api/games/{code}").json()
    assert "password_hash" not in room
    assert "player1_token" not in room
    assert "player2_token" not in room


def test_win_updates_scoreboard(client):
    code, p1, p2 = create_game(client)

    def move(player, token, cell):
        return client.post("/api/games/move", json={
            "room_code": code, "player_name": player, "move": cell,
            "player_token": token})
    # X wins across the top row: X0 O3 X1 O4 X2
    move("P1", p1, 0); move("P2", p2, 3)
    move("P1", p1, 1); move("P2", p2, 4)
    room = move("P1", p1, 2).json()["room"]
    assert room["winner"] == "X"
    assert room["scores"]["X"] == 1


# ---------- Admin ----------

def test_admin_login_and_expiry(client, monkeypatch):
    r = client.post("/api/admin/login", json={
        "username": "admin", "password": "test-admin-pw"})
    assert r.status_code == 200
    token = r.json()["token"]
    assert client.get(f"/api/admin/verify?token={token}").status_code == 200
    assert client.get("/api/admin/verify?token=garbage").status_code == 401


def test_admin_bad_password(client):
    r = client.post("/api/admin/login", json={
        "username": "admin", "password": "wrong"})
    assert r.status_code == 401
