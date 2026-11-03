"""
DOMAINE - Port du dépôt de clés RSA
"""
from abc import ABC, abstractmethod
from typing import Optional

from .models import RsaKeyPair


class KeyRepositoryInterface(ABC):
    @abstractmethod
    def get(self, owner_id: str) -> Optional[RsaKeyPair]: ...

    @abstractmethod
    def save(self, keypair: RsaKeyPair) -> RsaKeyPair: ...
