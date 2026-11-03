"""
DOMAINE - Modèles du module Crypt (paire de clés RSA, format des chiffrés).
Pur Python, aucune dépendance framework.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple

from .exceptions import InvalidCiphertextError

# Préfixe de version du format stocké en base : "rsa1:<bloc hex>:<bloc hex>..."
CIPHERTEXT_PREFIX = "rsa1"


@dataclass
class RsaKeyPair:
    owner_id: str  # id de la discussion propriétaire des clés
    e: int
    n: int
    d: int
    bits: int
    created_at: datetime

    @property
    def public_key(self) -> Tuple[int, int]:
        return (self.e, self.n)

    @property
    def private_key(self) -> Tuple[int, int]:
        return (self.d, self.n)

    @property
    def fingerprint(self) -> str:
        """Empreinte courte de la clé publique (affichage / vérification)."""
        import hashlib

        digest = hashlib.sha256(f"{self.e}:{self.n}".encode()).hexdigest()
        return ":".join(digest[i:i + 2] for i in range(0, 32, 2)).upper()


def serialize_blocks(blocks: List[int]) -> str:
    return ":".join([CIPHERTEXT_PREFIX] + [format(b, "x") for b in blocks])


def parse_blocks(serialized: str) -> List[int]:
    parts = serialized.split(":")
    if not parts or parts[0] != CIPHERTEXT_PREFIX:
        raise InvalidCiphertextError("Format de chiffré inconnu")
    try:
        return [int(p, 16) for p in parts[1:]]
    except ValueError:
        raise InvalidCiphertextError("Bloc chiffré invalide")
