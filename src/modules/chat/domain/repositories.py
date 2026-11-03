"""
DOMAINE - Repositories (Ports / Interfaces)
Définit les contrats de stockage sans savoir comment ils sont implémentés.
Les messages manipulés ici sont déjà chiffrés (champ `ciphertext`).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from .models import Discussion, ReadCursor


@dataclass
class StoredMessage:
    id: str
    chat_id: str
    sender_id: str
    ciphertext: str
    type: str
    created_at: datetime


@dataclass
class Membership:
    discussion_id: str
    user_id: str
    is_pinned: bool
    is_archived: bool
    last_read_at: Optional[datetime]


class ChatRepositoryInterface(ABC):
    # --- discussions -----------------------------------------------------
    @abstractmethod
    def create_discussion(self, discussion: Discussion) -> Discussion: ...

    @abstractmethod
    def get_discussion(self, discussion_id: str) -> Optional[Discussion]: ...

    @abstractmethod
    def find_direct_discussion(self, user_a: str, user_b: str) -> Optional[str]: ...

    @abstractmethod
    def list_memberships(self, user_id: str) -> List[Membership]: ...

    @abstractmethod
    def get_membership(self, discussion_id: str, user_id: str) -> Optional[Membership]: ...

    @abstractmethod
    def update_membership(self, discussion_id: str, user_id: str, **fields) -> Membership: ...

    @abstractmethod
    def read_cursors(self, discussion_id: str) -> List[ReadCursor]: ...

    # --- messages --------------------------------------------------------
    @abstractmethod
    def add_message(self, message: StoredMessage) -> StoredMessage: ...

    @abstractmethod
    def get_message(self, message_id: str) -> Optional[StoredMessage]: ...

    @abstractmethod
    def list_messages(self, discussion_id: str, limit: int, before: Optional[datetime]) -> List[StoredMessage]: ...

    @abstractmethod
    def last_message(self, discussion_id: str) -> Optional[StoredMessage]: ...

    @abstractmethod
    def count_unread(self, discussion_id: str, user_id: str, since: Optional[datetime]) -> int: ...

    # --- réactions -------------------------------------------------------
    @abstractmethod
    def toggle_reaction(self, message_id: str, user_id: str, emoji: str) -> bool:
        """Ajoute ou retire la réaction. Retourne True si ajoutée."""

    @abstractmethod
    def reactions_for(self, message_ids: List[str]) -> Dict[str, Dict[str, List[str]]]:
        """{message_id: {emoji: [user_id, ...]}}"""
