"""
INFRASTRUCTURE - Implémentation SQLAlchemy du dépôt Chat
"""
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from ..domain.models import Discussion, ReadCursor
from ..domain.repositories import ChatRepositoryInterface, Membership, StoredMessage
from .models import DiscussionMemberORM, DiscussionORM, MessageORM, ReactionORM


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _membership(row: DiscussionMemberORM) -> Membership:
    return Membership(
        discussion_id=row.discussion_id,
        user_id=row.user_id,
        is_pinned=row.is_pinned,
        is_archived=row.is_archived,
        last_read_at=row.last_read_at,
    )


def _message(row: MessageORM) -> StoredMessage:
    return StoredMessage(
        id=row.id,
        chat_id=row.discussion_id,
        sender_id=row.sender_id,
        ciphertext=row.ciphertext,
        type=row.type,
        created_at=row.created_at,
    )


class SqlChatRepository(ChatRepositoryInterface):
    def __init__(self, db: Session):
        self.db = db

    # --- discussions -----------------------------------------------------

    def create_discussion(self, discussion: Discussion) -> Discussion:
        self.db.add(
            DiscussionORM(
                id=discussion.id,
                title=discussion.title,
                is_group=discussion.is_group,
                created_by=discussion.created_by,
                created_at=discussion.created_at,
            )
        )
        self.db.flush()
        for uid in discussion.participant_ids:
            self.db.add(
                DiscussionMemberORM(
                    discussion_id=discussion.id,
                    user_id=uid,
                    joined_at=discussion.created_at,
                    # Le créateur a « lu » la discussion à sa création
                    last_read_at=discussion.created_at if uid == discussion.created_by else None,
                )
            )
        self.db.commit()
        return discussion

    def get_discussion(self, discussion_id: str) -> Optional[Discussion]:
        row = self.db.get(DiscussionORM, discussion_id)
        if not row:
            return None
        member_ids = list(
            self.db.scalars(
                select(DiscussionMemberORM.user_id).where(DiscussionMemberORM.discussion_id == discussion_id)
            )
        )
        return Discussion(
            id=row.id,
            title=row.title,
            is_group=row.is_group,
            participant_ids=member_ids,
            created_at=row.created_at,
            created_by=row.created_by,
        )

    def find_direct_discussion(self, user_a: str, user_b: str) -> Optional[str]:
        m1, m2 = aliased(DiscussionMemberORM), aliased(DiscussionMemberORM)
        stmt = (
            select(DiscussionORM.id)
            .join(m1, m1.discussion_id == DiscussionORM.id)
            .join(m2, m2.discussion_id == DiscussionORM.id)
            .where(DiscussionORM.is_group.is_(False), m1.user_id == user_a, m2.user_id == user_b)
            .limit(1)
        )
        return self.db.scalar(stmt)

    def list_memberships(self, user_id: str) -> List[Membership]:
        rows = self.db.scalars(select(DiscussionMemberORM).where(DiscussionMemberORM.user_id == user_id))
        return [_membership(r) for r in rows]

    def get_membership(self, discussion_id: str, user_id: str) -> Optional[Membership]:
        row = self.db.get(DiscussionMemberORM, (discussion_id, user_id))
        return _membership(row) if row else None

    def update_membership(self, discussion_id: str, user_id: str, **fields) -> Membership:
        row = self.db.get(DiscussionMemberORM, (discussion_id, user_id))
        for key, value in fields.items():
            setattr(row, key, value)
        self.db.commit()
        return _membership(row)

    def read_cursors(self, discussion_id: str) -> List[ReadCursor]:
        rows = self.db.scalars(
            select(DiscussionMemberORM).where(DiscussionMemberORM.discussion_id == discussion_id)
        )
        return [ReadCursor(user_id=r.user_id, last_read_at=r.last_read_at) for r in rows]

    # --- messages --------------------------------------------------------

    def add_message(self, message: StoredMessage) -> StoredMessage:
        self.db.add(
            MessageORM(
                id=message.id,
                discussion_id=message.chat_id,
                sender_id=message.sender_id,
                ciphertext=message.ciphertext,
                type=message.type,
                created_at=message.created_at,
            )
        )
        self.db.commit()
        return message

    def get_message(self, message_id: str) -> Optional[StoredMessage]:
        row = self.db.get(MessageORM, message_id)
        return _message(row) if row else None

    def list_messages(self, discussion_id: str, limit: int, before: Optional[datetime]) -> List[StoredMessage]:
        stmt = select(MessageORM).where(MessageORM.discussion_id == discussion_id)
        if before:
            stmt = stmt.where(MessageORM.created_at < before)
        stmt = stmt.order_by(MessageORM.created_at.desc()).limit(limit)
        rows = list(self.db.scalars(stmt))
        rows.reverse()  # ordre chronologique
        return [_message(r) for r in rows]

    def last_message(self, discussion_id: str) -> Optional[StoredMessage]:
        msgs = self.list_messages(discussion_id, 1, None)
        return msgs[0] if msgs else None

    def count_unread(self, discussion_id: str, user_id: str, since: Optional[datetime]) -> int:
        stmt = select(func.count()).select_from(MessageORM).where(
            MessageORM.discussion_id == discussion_id, MessageORM.sender_id != user_id
        )
        if since:
            stmt = stmt.where(MessageORM.created_at > since)
        return self.db.scalar(stmt) or 0

    # --- réactions -------------------------------------------------------

    def toggle_reaction(self, message_id: str, user_id: str, emoji: str) -> bool:
        row = self.db.get(ReactionORM, (message_id, user_id, emoji))
        if row:
            self.db.delete(row)
            added = False
        else:
            self.db.add(ReactionORM(message_id=message_id, user_id=user_id, emoji=emoji, created_at=_now()))
            added = True
        self.db.commit()
        return added

    def reactions_for(self, message_ids: List[str]) -> Dict[str, Dict[str, List[str]]]:
        result: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        if not message_ids:
            return result
        rows = self.db.scalars(
            select(ReactionORM)
            .where(ReactionORM.message_id.in_(message_ids))
            .order_by(ReactionORM.created_at)
        )
        for r in rows:
            result[r.message_id][r.emoji].append(r.user_id)
        return result
