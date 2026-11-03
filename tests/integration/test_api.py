"""
Tests d'intégration de l'API : comptes, discussions, messages chiffrés, temps réel.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from main import app
from src.core.database import SessionLocal
from src.modules.chat.infrastructure.models import MessageORM


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def register(client, name: str):
    username = f"{name}_{uuid.uuid4().hex[:6]}"
    r = client.post("/api/v1/auth/register", json={
        "username": username, "display_name": name.capitalize(), "password": "motdepasse123",
    })
    assert r.status_code == 201, r.text
    body = r.json()
    return {"id": body["user"]["id"], "username": username,
            "headers": {"Authorization": f"Bearer {body['access_token']}"},
            "token": body["access_token"]}


@pytest.fixture
def alice(client):
    return register(client, "alice")


@pytest.fixture
def bob(client):
    return register(client, "bob")


@pytest.fixture
def carol(client):
    return register(client, "carol")


def create_dm(client, a, b):
    r = client.post("/api/v1/chats", json={"member_ids": [b["id"]]}, headers=a["headers"])
    assert r.status_code == 201, r.text
    return r.json()


# --- Auth -------------------------------------------------------------------

def test_register_login_me(client):
    user = register(client, "dave")
    r = client.post("/api/v1/auth/login", json={"username": user["username"], "password": "motdepasse123"})
    assert r.status_code == 200
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert r.json()["username"] == user["username"]


def test_login_wrong_password(client, alice):
    r = client.post("/api/v1/auth/login", json={"username": alice["username"], "password": "nope-nope"})
    assert r.status_code == 401


def test_register_duplicate_and_weak_password(client, alice):
    r = client.post("/api/v1/auth/register", json={
        "username": alice["username"], "display_name": "X", "password": "motdepasse123"})
    assert r.status_code == 409
    r = client.post("/api/v1/auth/register", json={"username": "shorty_pw", "display_name": "X", "password": "123"})
    assert r.status_code == 400


def test_requires_auth(client):
    assert client.get("/api/v1/chats").status_code == 401
    assert client.get("/api/v1/chats", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_users_list_excludes_self(client, alice, bob):
    ids = [u["id"] for u in client.get("/api/v1/users", headers=alice["headers"]).json()]
    assert bob["id"] in ids and alice["id"] not in ids


# --- Discussions --------------------------------------------------------------

def test_direct_chat_is_reused(client, alice, bob):
    c1 = create_dm(client, alice, bob)
    c2 = client.post("/api/v1/chats", json={"member_ids": [alice["id"]]}, headers=bob["headers"]).json()
    assert c1["id"] == c2["id"]
    assert c1["title"] == "Bob" and c2["title"] == "Alice"
    assert c1["key_fingerprint"] and c1["key_bits"] == 512


def test_group_requires_title(client, alice, bob, carol):
    r = client.post("/api/v1/chats", json={"member_ids": [bob["id"], carol["id"]]}, headers=alice["headers"])
    assert r.status_code == 400
    r = client.post("/api/v1/chats", json={"member_ids": [bob["id"], carol["id"]], "title": "Projet Crypto"},
                    headers=alice["headers"])
    assert r.status_code == 201
    assert r.json()["is_group"] and len(r.json()["members"]) == 3


def test_non_member_forbidden(client, alice, bob, carol):
    chat = create_dm(client, alice, bob)
    r = client.get(f"/api/v1/chats/{chat['id']}/messages", headers=carol["headers"])
    assert r.status_code == 403
    r = client.post(f"/api/v1/chats/{chat['id']}/messages", json={"content": "intrus"}, headers=carol["headers"])
    assert r.status_code == 403


def test_pin_and_archive(client, alice, bob):
    chat = create_dm(client, alice, bob)
    r = client.patch(f"/api/v1/chats/{chat['id']}", json={"is_pinned": True, "is_archived": True},
                     headers=alice["headers"])
    assert r.json()["is_pinned"] and r.json()["is_archived"]
    # Préférence propre à Alice
    bob_view = client.get(f"/api/v1/chats/{chat['id']}", headers=bob["headers"]).json()
    assert not bob_view["is_pinned"] and not bob_view["is_archived"]


# --- Messages chiffrés --------------------------------------------------------

def test_messages_are_stored_encrypted(client, alice, bob):
    chat = create_dm(client, alice, bob)
    secret = "Le code du coffre est 4242 🔐"
    r = client.post(f"/api/v1/chats/{chat['id']}/messages", json={"content": secret}, headers=alice["headers"])
    assert r.status_code == 201
    msg = r.json()
    assert msg["content"] == secret

    # En base : uniquement le chiffré RSA
    with SessionLocal() as db:
        row = db.scalar(select(MessageORM).where(MessageORM.id == msg["id"]))
    assert row.ciphertext.startswith("rsa1:")
    assert secret not in row.ciphertext and "4242" not in row.ciphertext

    # Bob lit le message déchiffré
    history = client.get(f"/api/v1/chats/{chat['id']}/messages", headers=bob["headers"]).json()
    assert history[-1]["content"] == secret
    assert history[-1]["ciphertext"] is None

    with_cipher = client.get(f"/api/v1/chats/{chat['id']}/messages?include_cipher=true",
                             headers=bob["headers"]).json()
    assert with_cipher[-1]["ciphertext"] == row.ciphertext


def test_unread_and_read_receipts(client, alice, bob):
    chat = create_dm(client, alice, bob)
    cid = chat["id"]
    client.post(f"/api/v1/chats/{cid}/messages", json={"content": "Salut"}, headers=alice["headers"])
    client.post(f"/api/v1/chats/{cid}/messages", json={"content": "Ça va ?"}, headers=alice["headers"])

    assert client.get(f"/api/v1/chats/{cid}", headers=bob["headers"]).json()["unread_count"] == 2
    assert client.get(f"/api/v1/chats/{cid}", headers=alice["headers"]).json()["unread_count"] == 0
    msgs = client.get(f"/api/v1/chats/{cid}/messages", headers=alice["headers"]).json()
    assert all(m["status"] == "sent" for m in msgs)

    client.post(f"/api/v1/chats/{cid}/read", headers=bob["headers"])
    assert client.get(f"/api/v1/chats/{cid}", headers=bob["headers"]).json()["unread_count"] == 0
    msgs = client.get(f"/api/v1/chats/{cid}/messages", headers=alice["headers"]).json()
    assert all(m["status"] == "read" for m in msgs)


def test_long_message_multiple_blocks(client, alice, bob):
    chat = create_dm(client, alice, bob)
    text = "Bloc " * 800  # 4000 caractères -> nombreux blocs RSA
    r = client.post(f"/api/v1/chats/{chat['id']}/messages", json={"content": text}, headers=alice["headers"])
    assert r.status_code == 201
    history = client.get(f"/api/v1/chats/{chat['id']}/messages", headers=bob["headers"]).json()
    assert history[-1]["content"] == text


def test_empty_and_too_long_messages_rejected(client, alice, bob):
    chat = create_dm(client, alice, bob)
    url = f"/api/v1/chats/{chat['id']}/messages"
    assert client.post(url, json={"content": "   "}, headers=alice["headers"]).status_code == 400
    assert client.post(url, json={"content": "x" * 4001}, headers=alice["headers"]).status_code == 422


def test_reactions_toggle(client, alice, bob):
    chat = create_dm(client, alice, bob)
    msg = client.post(f"/api/v1/chats/{chat['id']}/messages", json={"content": "GG"},
                      headers=alice["headers"]).json()
    url = f"/api/v1/chats/{chat['id']}/messages/{msg['id']}/reactions"

    r = client.post(url, json={"emoji": "🔥"}, headers=bob["headers"]).json()
    assert r["reactions"] == [{"emoji": "🔥", "count": 1, "user_ids": [bob["id"]]}]
    r = client.post(url, json={"emoji": "🔥"}, headers=alice["headers"]).json()
    assert r["reactions"][0]["count"] == 2
    r = client.post(url, json={"emoji": "🔥"}, headers=bob["headers"]).json()
    assert r["reactions"][0]["user_ids"] == [alice["id"]]

    assert client.post(url, json={"emoji": "💩"}, headers=bob["headers"]).status_code == 400


def test_list_sorted_pinned_first(client, alice, bob, carol):
    c_bob = create_dm(client, alice, bob)
    c_carol = create_dm(client, alice, carol)
    client.post(f"/api/v1/chats/{c_carol['id']}/messages", json={"content": "récent"}, headers=alice["headers"])
    client.patch(f"/api/v1/chats/{c_bob['id']}", json={"is_pinned": True}, headers=alice["headers"])
    ids = [c["id"] for c in client.get("/api/v1/chats", headers=alice["headers"]).json()]
    assert ids.index(c_bob["id"]) < ids.index(c_carol["id"])


# --- Démo RSA -----------------------------------------------------------------

def test_crypt_demo_roundtrip(client, alice):
    keys = client.post("/api/v1/crypt/keys", json={"bits": 256}, headers=alice["headers"]).json()
    enc = client.post("/api/v1/crypt/encrypt", json={"text": "bonjour", "e": keys["e"], "n": keys["n"]},
                      headers=alice["headers"]).json()
    dec = client.post("/api/v1/crypt/decrypt", json={"blocks": enc["blocks"], "d": keys["d"], "n": keys["n"]},
                      headers=alice["headers"]).json()
    assert dec["text"] == "bonjour"


# --- Temps réel ---------------------------------------------------------------

def test_websocket_receives_new_message_and_typing(client, alice, bob):
    chat = create_dm(client, alice, bob)
    with client.websocket_connect(f"/api/v1/ws?token={bob['token']}") as ws_bob:
        assert ws_bob.receive_json() == {"type": "presence", "user_id": bob["id"], "is_online": True}

        with client.websocket_connect(f"/api/v1/ws?token={alice['token']}") as ws_alice:
            assert ws_bob.receive_json()["user_id"] == alice["id"]  # Alice en ligne
            ws_alice.receive_json()  # sa propre présence

            ws_alice.send_json({"type": "typing", "chat_id": chat["id"], "is_typing": True})
            evt = ws_bob.receive_json()
            assert evt == {"type": "typing", "chat_id": chat["id"], "user_id": alice["id"], "is_typing": True}

            client.post(f"/api/v1/chats/{chat['id']}/messages", json={"content": "temps réel !"},
                        headers=alice["headers"])
            evt = ws_bob.receive_json()
            assert evt["type"] == "message.new"
            assert evt["message"]["content"] == "temps réel !"


def test_websocket_rejects_bad_token(client):
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/v1/ws?token=invalid") as ws:
            ws.receive_json()
