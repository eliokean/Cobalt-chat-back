"""
DOMAINE - Modèle Utilisateur et règles d'invariants.
Pur Python, aucune dépendance framework.
"""
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .exceptions import InvalidUsernameError, WeakPasswordError

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")
MIN_PASSWORD_LENGTH = 8


@dataclass
class User:
    id: str
    username: str
    display_name: str
    created_at: datetime
    last_seen_at: Optional[datetime] = None
    role: str = ""

    @staticmethod
    def normalize_username(username: str) -> str:
        return username.strip().lower()

    @staticmethod
    def validate_username(username: str) -> None:
        if not USERNAME_RE.match(username):
            raise InvalidUsernameError(
                "Le nom d'utilisateur doit faire 3 à 32 caractères (lettres, chiffres, _ . -)."
            )

    @staticmethod
    def validate_password(password: str) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise WeakPasswordError(
                f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères."
            )
