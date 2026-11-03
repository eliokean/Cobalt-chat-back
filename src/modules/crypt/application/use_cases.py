"""
APPLICATION - Cas d'utilisation Crypt

MessageCryptoService : utilisé par le module Chat pour chiffrer les messages
avant stockage et les déchiffrer à la lecture (une paire de clés RSA par discussion).
"""
from datetime import datetime, timezone
from typing import Dict

from ..domain import rsa
from ..domain.exceptions import InvalidCiphertextError, KeyNotFoundError
from ..domain.models import RsaKeyPair, parse_blocks, serialize_blocks
from ..domain.repositories import KeyRepositoryInterface
from .dto import (
    DecryptInputDTO,
    DecryptOutputDTO,
    EncryptInputDTO,
    EncryptOutputDTO,
    KeyPairOutputDTO,
    PublicKeyOutputDTO,
)


class MessageCryptoService:
    def __init__(self, repo: KeyRepositoryInterface, key_bits: int):
        self.repo = repo
        self.key_bits = key_bits
        self._cache: Dict[str, RsaKeyPair] = {}

    def create_keys(self, owner_id: str) -> RsaKeyPair:
        (e, n), (d, _) = rsa.generate_keypair(self.key_bits)
        keypair = RsaKeyPair(
            owner_id=owner_id, e=e, n=n, d=d, bits=self.key_bits,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self._cache[owner_id] = self.repo.save(keypair)
        return keypair

    def get_keys(self, owner_id: str) -> RsaKeyPair:
        if owner_id not in self._cache:
            kp = self.repo.get(owner_id)
            if kp is None:
                raise KeyNotFoundError(f"Aucune clé pour {owner_id}")
            self._cache[owner_id] = kp
        return self._cache[owner_id]

    def get_or_create_keys(self, owner_id: str) -> RsaKeyPair:
        try:
            return self.get_keys(owner_id)
        except KeyNotFoundError:
            return self.create_keys(owner_id)

    def encrypt(self, owner_id: str, plaintext: str) -> str:
        kp = self.get_or_create_keys(owner_id)
        return serialize_blocks(rsa.encrypt_text(plaintext, kp.public_key))

    def decrypt(self, owner_id: str, ciphertext: str) -> str:
        kp = self.get_keys(owner_id)
        try:
            return rsa.decrypt_text(parse_blocks(ciphertext), kp.private_key)
        except (ValueError, UnicodeDecodeError) as exc:
            raise InvalidCiphertextError(str(exc))

    def public_key(self, owner_id: str) -> PublicKeyOutputDTO:
        kp = self.get_or_create_keys(owner_id)
        return PublicKeyOutputDTO(e=str(kp.e), n=str(kp.n), bits=kp.bits, fingerprint=kp.fingerprint)


# --- Démonstration pédagogique (clés fournies par l'appelant) ---------------

class GenerateKeysUseCase:
    def execute(self, bits: int) -> KeyPairOutputDTO:
        (e, n), (d, _) = rsa.generate_keypair(bits)
        return KeyPairOutputDTO(e=str(e), n=str(n), d=str(d), bits=n.bit_length())


class EncryptUseCase:
    def execute(self, dto: EncryptInputDTO) -> EncryptOutputDTO:
        blocks = rsa.encrypt_text(dto.text, (int(dto.e), int(dto.n)))
        return EncryptOutputDTO(blocks=[str(b) for b in blocks])


class DecryptUseCase:
    def execute(self, dto: DecryptInputDTO) -> DecryptOutputDTO:
        try:
            text = rsa.decrypt_text([int(b) for b in dto.blocks], (int(dto.d), int(dto.n)))
        except (ValueError, UnicodeDecodeError) as exc:
            raise InvalidCiphertextError(str(exc))
        return DecryptOutputDTO(text=text)
