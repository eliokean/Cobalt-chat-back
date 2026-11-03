"""
APPLICATION - Cas d'Utilisation (Use Cases)
Orchestre l'exécution des règles du domaine, le chiffrement RSA et les repositories.

Flux d'un message :
  texte clair --(validate)--> MessageCryptoService.encrypt --> base (ciphertext)
  base (ciphertext) --> MessageCryptoService.decrypt --> DTO (texte clair) --> client
"""
import uuid
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

from src.modules.auth.application.dto import UserOutputDTO
from src.modules.auth.domain.models import User
from src.modules.auth.domain.repositories import UserRepositoryInterface
from src.modules.crypt.application.use_cases import MessageCryptoService
from src.modules.crypt.domain.exceptions import CryptoDomainException

from ..domain.exceptions import (
    DiscussionNotFoundError,
    InvalidDiscussionError,
    MessageNotFoundError,
    NotAMemberError,
)
from ..domain.models import Discussion, Message, Reaction, ReadCursor, message_status
from ..domain.repositories import ChatRepositoryInterface, Membership, StoredMessage
from .dto import (
    CreateDiscussionInputDTO,
    DiscussionOutputDTO,
    MessageOutputDTO,
    ReactionOutputDTO,
    ReadReceiptOutputDTO,
    SendMessageInputDTO,
    UpdateMembershipInputDTO,
)

UNREADABLE = "[message illisible : déchiffrement impossible]"


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ChatContext:
    """Dépendances partagées par les use cases + construction des DTO."""

    def __init__(
        self,
        repo: ChatRepositoryInterface,
        users: UserRepositoryInterface,
        crypto: MessageCryptoService,
        is_online: Callable[[str], bool],
    ):
        self.repo = repo
        self.users = users
        self.crypto = crypto
        self.is_online = is_online

    # --- contrôles d'accès ---------------------------------------------

    def require_member(self, chat_id: str, user_id: str) -> Tuple[Discussion, Membership]:
        discussion = self.repo.get_discussion(chat_id)
        if discussion is None:
            raise DiscussionNotFoundError("Discussion introuvable.")
        membership = self.repo.get_membership(chat_id, user_id)
        if membership is None:
            raise NotAMemberError("Vous ne participez pas à cette discussion.")
        return discussion, membership

    # --- construction des DTO ------------------------------------------

    def users_by_id(self, ids: List[str]) -> Dict[str, User]:
        return {u.id: u for u in self.users.get_many(list(set(ids)))}

    def decrypt(self, stored: StoredMessage) -> str:
        try:
            return self.crypto.decrypt(stored.chat_id, stored.ciphertext)
        except CryptoDomainException:
            return UNREADABLE

    def message_dto(
        self,
        stored: StoredMessage,
        cursors: List[ReadCursor],
        reactions: Dict[str, List[str]],
        users: Dict[str, User],
        include_cipher: bool = False,
        plaintext: Optional[str] = None,
    ) -> MessageOutputDTO:
        sender = users.get(stored.sender_id)
        return MessageOutputDTO(
            id=stored.id,
            chat_id=stored.chat_id,
            sender_id=stored.sender_id,
            sender_name=sender.display_name if sender else None,
            content=plaintext if plaintext is not None else self.decrypt(stored),
            type=stored.type,
            created_at=stored.created_at,
            status=message_status(stored.created_at, stored.sender_id, cursors),
            reactions=[
                ReactionOutputDTO(emoji=e, count=len(uids), user_ids=uids) for e, uids in reactions.items()
            ],
            ciphertext=stored.ciphertext if include_cipher else None,
        )

    def discussion_dto(self, discussion: Discussion, membership: Membership, viewer_id: str) -> DiscussionOutputDTO:
        users = self.users_by_id(discussion.participant_ids)
        cursors = self.repo.read_cursors(discussion.id)
        last = self.repo.last_message(discussion.id)
        last_dto = None
        if last:
            reactions = self.repo.reactions_for([last.id]).get(last.id, {})
            last_dto = self.message_dto(last, cursors, reactions, users)

        if discussion.is_group:
            title = discussion.title or "Groupe"
        else:
            other = next((users[u] for u in discussion.participant_ids if u != viewer_id and u in users), None)
            title = other.display_name if other else "Conversation"

        try:
            kp = self.crypto.get_keys(discussion.id)
            fingerprint, bits = kp.fingerprint, kp.bits
        except CryptoDomainException:
            fingerprint, bits = None, None

        return DiscussionOutputDTO(
            id=discussion.id,
            title=title,
            is_group=discussion.is_group,
            members=[
                UserOutputDTO.from_domain(users[uid], self.is_online(uid))
                for uid in discussion.participant_ids
                if uid in users
            ],
            is_pinned=membership.is_pinned,
            is_archived=membership.is_archived,
            unread_count=self.repo.count_unread(discussion.id, viewer_id, membership.last_read_at),
            last_message=last_dto,
            read_cursors={c.user_id: c.last_read_at for c in cursors},
            created_at=discussion.created_at,
            updated_at=last.created_at if last else discussion.created_at,
            key_fingerprint=fingerprint,
            key_bits=bits,
        )


# ---------------------------------------------------------------------------
# Discussions
# ---------------------------------------------------------------------------

class ListDiscussionsUseCase:
    def __init__(self, ctx: ChatContext):
        self.ctx = ctx

    def execute(self, user_id: str) -> List[DiscussionOutputDTO]:
        result = []
        for m in self.ctx.repo.list_memberships(user_id):
            discussion = self.ctx.repo.get_discussion(m.discussion_id)
            if discussion:
                result.append(self.ctx.discussion_dto(discussion, m, user_id))
        result.sort(key=lambda d: (not d.is_pinned, -d.updated_at.timestamp()))
        return result


class GetDiscussionUseCase:
    def __init__(self, ctx: ChatContext):
        self.ctx = ctx

    def execute(self, user_id: str, chat_id: str) -> DiscussionOutputDTO:
        discussion, membership = self.ctx.require_member(chat_id, user_id)
        return self.ctx.discussion_dto(discussion, membership, user_id)


class CreateDiscussionUseCase:
    def __init__(self, ctx: ChatContext):
        self.ctx = ctx

    def execute(self, user_id: str, dto: CreateDiscussionInputDTO) -> Tuple[Discussion, bool]:
        """Retourne (discussion, créée). Une conversation privée existante est réutilisée."""
        others = [uid for uid in dict.fromkeys(dto.member_ids) if uid != user_id]
        if not others:
            raise InvalidDiscussionError("Choisissez au moins un autre participant.")
        if len(self.ctx.users.get_many(others)) != len(others):
            raise InvalidDiscussionError("Participant inconnu.")

        is_group = dto.is_group if dto.is_group is not None else (bool(dto.title) or len(others) > 1)

        if not is_group:
            if len(others) != 1:
                raise InvalidDiscussionError("Une conversation privée réunit exactement 2 personnes.")
            existing = self.ctx.repo.find_direct_discussion(user_id, others[0])
            if existing:
                discussion = self.ctx.repo.get_discussion(existing)
                # Rouvrir une conversation archivée
                self.ctx.repo.update_membership(existing, user_id, is_archived=False)
                return discussion, False

        discussion = Discussion(
            id=str(uuid.uuid4()),
            title=dto.title.strip() if dto.title else None,
            is_group=is_group,
            participant_ids=[user_id] + others,
            created_at=utcnow(),
            created_by=user_id,
        )
        discussion.validate()
        self.ctx.repo.create_discussion(discussion)
        # Une paire de clés RSA dédiée à la discussion
        self.ctx.crypto.create_keys(discussion.id)
        return discussion, True


class UpdateMembershipUseCase:
    def __init__(self, ctx: ChatContext):
        self.ctx = ctx

    def execute(self, user_id: str, chat_id: str, dto: UpdateMembershipInputDTO) -> DiscussionOutputDTO:
        discussion, _ = self.ctx.require_member(chat_id, user_id)
        fields = dto.model_dump(exclude_none=True)
        membership = self.ctx.repo.update_membership(chat_id, user_id, **fields) if fields else \
            self.ctx.repo.get_membership(chat_id, user_id)
        return self.ctx.discussion_dto(discussion, membership, user_id)


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

class GetChatHistoryUseCase:
    def __init__(self, ctx: ChatContext):
        self.ctx = ctx

    def execute(
        self,
        user_id: str,
        chat_id: str,
        limit: int = 50,
        before: Optional[datetime] = None,
        include_cipher: bool = False,
    ) -> List[MessageOutputDTO]:
        discussion, _ = self.ctx.require_member(chat_id, user_id)
        stored = self.ctx.repo.list_messages(chat_id, limit, before)
        cursors = self.ctx.repo.read_cursors(chat_id)
        reactions = self.ctx.repo.reactions_for([m.id for m in stored])
        users = self.ctx.users_by_id(discussion.participant_ids + [m.sender_id for m in stored])
        return [
            self.ctx.message_dto(m, cursors, reactions.get(m.id, {}), users, include_cipher)
            for m in stored
        ]


class SendMessageUseCase:
    def __init__(self, ctx: ChatContext):
        self.ctx = ctx

    def execute(self, user_id: str, chat_id: str, dto: SendMessageInputDTO) -> Tuple[MessageOutputDTO, List[str]]:
        discussion, _ = self.ctx.require_member(chat_id, user_id)

        # 1. Entité du domaine (texte clair) + invariants
        message = Message(
            id=str(uuid.uuid4()),
            chat_id=chat_id,
            sender_id=user_id,
            content=dto.content,
            created_at=utcnow(),
            type=dto.type,
        )
        message.validate()

        # 2. Chiffrement RSA avant persistance : la base ne voit que le chiffré
        stored = StoredMessage(
            id=message.id,
            chat_id=chat_id,
            sender_id=user_id,
            ciphertext=self.ctx.crypto.encrypt(chat_id, message.content),
            type=message.type,
            created_at=message.created_at,
        )
        self.ctx.repo.add_message(stored)

        # 3. L'expéditeur a lu son propre message ; on désarchive pour tout le monde
        self.ctx.repo.update_membership(chat_id, user_id, last_read_at=message.created_at)
        for uid in discussion.participant_ids:
            m = self.ctx.repo.get_membership(chat_id, uid)
            if m and m.is_archived:
                self.ctx.repo.update_membership(chat_id, uid, is_archived=False)

        users = self.ctx.users_by_id([user_id])
        out = self.ctx.message_dto(
            stored, self.ctx.repo.read_cursors(chat_id), {}, users, plaintext=message.content
        )
        return out, discussion.participant_ids


class MarkReadUseCase:
    def __init__(self, ctx: ChatContext):
        self.ctx = ctx

    def execute(self, user_id: str, chat_id: str) -> Tuple[ReadReceiptOutputDTO, List[str]]:
        discussion, _ = self.ctx.require_member(chat_id, user_id)
        now = utcnow()
        self.ctx.repo.update_membership(chat_id, user_id, last_read_at=now)
        return ReadReceiptOutputDTO(chat_id=chat_id, user_id=user_id, read_at=now), discussion.participant_ids


class ToggleReactionUseCase:
    def __init__(self, ctx: ChatContext):
        self.ctx = ctx

    def execute(
        self, user_id: str, chat_id: str, message_id: str, emoji: str
    ) -> Tuple[List[ReactionOutputDTO], List[str]]:
        discussion, _ = self.ctx.require_member(chat_id, user_id)
        stored = self.ctx.repo.get_message(message_id)
        if stored is None or stored.chat_id != chat_id:
            raise MessageNotFoundError("Message introuvable.")
        Reaction(message_id=message_id, user_id=user_id, emoji=emoji).validate()
        self.ctx.repo.toggle_reaction(message_id, user_id, emoji)
        reactions = self.ctx.repo.reactions_for([message_id]).get(message_id, {})
        return (
            [ReactionOutputDTO(emoji=e, count=len(u), user_ids=u) for e, u in reactions.items()],
            discussion.participant_ids,
        )
