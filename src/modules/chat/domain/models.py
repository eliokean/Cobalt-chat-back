"""
DOMAINE - Modèles Métier (Entités & Objets Valeurs)
Règle d'or : Pur Python, aucune dépendance vers des frameworks (ni FastAPI, ni SQL).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from .exceptions import (
    EmptyMessageError,
    InvalidDiscussionError,
    InvalidReactionError,
    MessageTooLongError,
)

MAX_MESSAGE_LENGTH = 4000
MAX_GROUP_TITLE_LENGTH = 64
# Identifiants des réactions (icônes rendues côté front par lucide-react)
ALLOWED_REACTIONS = ("like", "love", "laugh", "fire", "celebrate", "sad")


@dataclass
class Message:
    id: str
    chat_id: str
    sender_id: str
    content: str  # texte en clair (le chiffrement est fait à la persistance)
    created_at: datetime
    type: str = "text"

    def validate(self) -> None:
        """Règles d'invariants métier."""
        if not self.content or not self.content.strip():
            raise EmptyMessageError("Le contenu du message ne peut pas être vide.")
        if len(self.content) > MAX_MESSAGE_LENGTH:
            raise MessageTooLongError(
                f"Le message dépasse la taille maximale autorisée ({MAX_MESSAGE_LENGTH} caractères)."
            )


@dataclass
class Discussion:
    id: str
    title: Optional[str]
    is_group: bool
    participant_ids: List[str]
    created_at: datetime
    created_by: Optional[str] = None
    is_pinned: bool = False

    def validate(self) -> None:
        unique = set(self.participant_ids)
        if len(unique) != len(self.participant_ids):
            raise InvalidDiscussionError("Participants en double.")
        if self.is_group:
            if not self.title or not self.title.strip():
                raise InvalidDiscussionError("Un groupe doit avoir un nom.")
            if len(self.title) > MAX_GROUP_TITLE_LENGTH:
                raise InvalidDiscussionError("Nom de groupe trop long.")
            if len(unique) < 2:
                raise InvalidDiscussionError("Un groupe doit compter au moins 2 participants.")
        elif len(unique) != 2:
            raise InvalidDiscussionError("Une conversation privée réunit exactement 2 personnes.")


@dataclass(frozen=True)
class Reaction:
    message_id: str
    user_id: str
    emoji: str

    def validate(self) -> None:
        if self.emoji not in ALLOWED_REACTIONS:
            raise InvalidReactionError(f"Réaction non autorisée : {self.emoji}")


@dataclass
class ReadCursor:
    """Dernière lecture d'une discussion par un membre."""
    user_id: str
    last_read_at: Optional[datetime] = None


def message_status(created_at: datetime, sender_id: str, cursors: List[ReadCursor]) -> str:
    """'read' si tous les autres membres ont lu le message, sinon 'sent'."""
    others = [c for c in cursors if c.user_id != sender_id]
    if others and all(c.last_read_at and c.last_read_at >= created_at for c in others):
        return "read"
    return "sent"
