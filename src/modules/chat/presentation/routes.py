"""
PRESENTATION - Routes FastAPI (Contrôleurs HTTP) + WebSocket temps réel.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.concurrency import run_in_threadpool

from src.core.database import SessionLocal
from src.core.exceptions import UnauthorizedException
from src.core.realtime import manager
from src.modules.auth.application.use_cases import utcnow
from src.modules.auth.domain.models import User
from src.modules.auth.infrastructure.repositories import SqlUserRepository
from src.modules.auth.presentation.dependencies import get_current_user, resolve_user_from_token

from ..application.dto import (
    CreateDiscussionInputDTO,
    DiscussionOutputDTO,
    MessageOutputDTO,
    ReactionInputDTO,
    ReadReceiptOutputDTO,
    SendMessageInputDTO,
    UpdateMembershipInputDTO,
)
from ..application.use_cases import (
    ChatContext,
    CreateDiscussionUseCase,
    GetChatHistoryUseCase,
    GetDiscussionUseCase,
    ListDiscussionsUseCase,
    MarkReadUseCase,
    SendMessageUseCase,
    ToggleReactionUseCase,
    UpdateMembershipUseCase,
)
from ..domain.exceptions import (
    DiscussionNotFoundError,
    DomainException,
    MessageNotFoundError,
    NotAMemberError,
)
from ..infrastructure.repositories import SqlChatRepository
from .dependencies import get_chat_context

router = APIRouter(prefix="/chats", tags=["Chat"])
ws_router = APIRouter(tags=["Temps réel"])


def _http_error(exc: DomainException) -> HTTPException:
    if isinstance(exc, (DiscussionNotFoundError, MessageNotFoundError)):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, NotAMemberError):
        return HTTPException(status.HTTP_403_FORBIDDEN, str(exc))
    return HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


# ---------------------------------------------------------------------------
# Discussions
# ---------------------------------------------------------------------------

@router.get("", response_model=List[DiscussionOutputDTO])
def list_discussions(user: User = Depends(get_current_user), ctx: ChatContext = Depends(get_chat_context)):
    return ListDiscussionsUseCase(ctx).execute(user.id)


@router.post("", response_model=DiscussionOutputDTO, status_code=status.HTTP_201_CREATED)
def create_discussion(
    payload: CreateDiscussionInputDTO,
    user: User = Depends(get_current_user),
    ctx: ChatContext = Depends(get_chat_context),
):
    try:
        discussion, created = CreateDiscussionUseCase(ctx).execute(user.id, payload)
    except DomainException as e:
        raise _http_error(e)

    if created:
        # Chaque autre membre reçoit la discussion vue de son côté (titre, non-lus...)
        for uid in discussion.participant_ids:
            if uid != user.id:
                m = ctx.repo.get_membership(discussion.id, uid)
                manager.notify([uid], {
                    "type": "chat.new",
                    "chat": ctx.discussion_dto(discussion, m, uid).model_dump(mode="json"),
                })
    return ctx.discussion_dto(discussion, ctx.repo.get_membership(discussion.id, user.id), user.id)


@router.get("/{chat_id}", response_model=DiscussionOutputDTO)
def get_discussion(chat_id: str, user: User = Depends(get_current_user), ctx: ChatContext = Depends(get_chat_context)):
    try:
        return GetDiscussionUseCase(ctx).execute(user.id, chat_id)
    except DomainException as e:
        raise _http_error(e)


@router.patch("/{chat_id}", response_model=DiscussionOutputDTO)
def update_discussion(
    chat_id: str,
    payload: UpdateMembershipInputDTO,
    user: User = Depends(get_current_user),
    ctx: ChatContext = Depends(get_chat_context),
):
    """Épingler / archiver (préférences propres à l'utilisateur)."""
    try:
        return UpdateMembershipUseCase(ctx).execute(user.id, chat_id, payload)
    except DomainException as e:
        raise _http_error(e)


@router.post("/{chat_id}/read", response_model=ReadReceiptOutputDTO)
def mark_read(chat_id: str, user: User = Depends(get_current_user), ctx: ChatContext = Depends(get_chat_context)):
    try:
        receipt, members = MarkReadUseCase(ctx).execute(user.id, chat_id)
    except DomainException as e:
        raise _http_error(e)
    manager.notify(members, {"type": "chat.read", **receipt.model_dump(mode="json")})
    return receipt


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

@router.get("/{chat_id}/messages", response_model=List[MessageOutputDTO])
def get_messages(
    chat_id: str,
    limit: int = Query(50, ge=1, le=200),
    before: Optional[datetime] = None,
    include_cipher: bool = False,
    user: User = Depends(get_current_user),
    ctx: ChatContext = Depends(get_chat_context),
):
    """Historique déchiffré. `include_cipher=true` ajoute le chiffré RSA stocké en base."""
    try:
        return GetChatHistoryUseCase(ctx).execute(user.id, chat_id, limit, before, include_cipher)
    except DomainException as e:
        raise _http_error(e)


@router.post("/{chat_id}/messages", response_model=MessageOutputDTO, status_code=status.HTTP_201_CREATED)
def send_message(
    chat_id: str,
    payload: SendMessageInputDTO,
    user: User = Depends(get_current_user),
    ctx: ChatContext = Depends(get_chat_context),
):
    try:
        message, members = SendMessageUseCase(ctx).execute(user.id, chat_id, payload)
    except DomainException as e:
        raise _http_error(e)
    manager.notify(members, {"type": "message.new", "message": message.model_dump(mode="json")})
    return message


@router.post("/{chat_id}/messages/{message_id}/reactions")
def toggle_reaction(
    chat_id: str,
    message_id: str,
    payload: ReactionInputDTO,
    user: User = Depends(get_current_user),
    ctx: ChatContext = Depends(get_chat_context),
):
    try:
        reactions, members = ToggleReactionUseCase(ctx).execute(user.id, chat_id, message_id, payload.emoji)
    except DomainException as e:
        raise _http_error(e)
    body = {"chat_id": chat_id, "message_id": message_id, "reactions": [r.model_dump() for r in reactions]}
    manager.notify(members, {"type": "message.reactions", **body})
    return body


# ---------------------------------------------------------------------------
# WebSocket : présence, « en train d'écrire », réception des événements
# ---------------------------------------------------------------------------

def _authenticate(token: str) -> User:
    db = SessionLocal()
    try:
        return resolve_user_from_token(token, SqlUserRepository(db))
    finally:
        db.close()


def _member_ids(chat_id: str, user_id: str) -> List[str]:
    """Membres de la discussion si user_id en fait partie, sinon liste vide."""
    db = SessionLocal()
    try:
        repo = SqlChatRepository(db)
        if repo.get_membership(chat_id, user_id) is None:
            return []
        d = repo.get_discussion(chat_id)
        return d.participant_ids if d else []
    finally:
        db.close()


def _touch_last_seen(user_id: str) -> str:
    db = SessionLocal()
    try:
        now = utcnow()
        SqlUserRepository(db).touch_last_seen(user_id, now)
        return now.isoformat()
    finally:
        db.close()


@ws_router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str = Query(...)):
    try:
        user = await run_in_threadpool(_authenticate, token)
    except UnauthorizedException:
        await ws.close(code=4401)
        return

    if await manager.connect(user.id, ws):
        await manager.broadcast({"type": "presence", "user_id": user.id, "is_online": True})

    try:
        while True:
            data = await ws.receive_json()
            kind = data.get("type")
            if kind == "typing" and isinstance(data.get("chat_id"), str):
                members = await run_in_threadpool(_member_ids, data["chat_id"], user.id)
                others = [m for m in members if m != user.id]
                await manager.send(others, {
                    "type": "typing",
                    "chat_id": data["chat_id"],
                    "user_id": user.id,
                    "is_typing": bool(data.get("is_typing")),
                })
            elif kind == "ping":
                await ws.send_json({"type": "pong"})
    except (WebSocketDisconnect, RuntimeError, ValueError):
        pass
    finally:
        if manager.disconnect(user.id, ws):
            last_seen = await run_in_threadpool(_touch_last_seen, user.id)
            await manager.broadcast({
                "type": "presence", "user_id": user.id, "is_online": False, "last_seen_at": last_seen,
            })
