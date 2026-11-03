"""
PRESENTATION - Routes Crypt : démonstration de l'algorithme RSA.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from src.modules.auth.presentation.dependencies import get_current_user

from ..application.dto import (
    DecryptInputDTO,
    DecryptOutputDTO,
    EncryptInputDTO,
    EncryptOutputDTO,
    KeyGenInputDTO,
    KeyPairOutputDTO,
)
from ..application.use_cases import DecryptUseCase, EncryptUseCase, GenerateKeysUseCase
from ..domain.exceptions import InvalidCiphertextError

router = APIRouter(prefix="/crypt", tags=["Crypt (démo RSA)"], dependencies=[Depends(get_current_user)])


@router.post("/keys", response_model=KeyPairOutputDTO)
def generate_keys(payload: KeyGenInputDTO):
    return GenerateKeysUseCase().execute(payload.bits)


@router.post("/encrypt", response_model=EncryptOutputDTO)
def encrypt(payload: EncryptInputDTO):
    try:
        return EncryptUseCase().execute(payload)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.post("/decrypt", response_model=DecryptOutputDTO)
def decrypt(payload: DecryptInputDTO):
    try:
        return DecryptUseCase().execute(payload)
    except (InvalidCiphertextError, ValueError) as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Déchiffrement impossible : {e}")
