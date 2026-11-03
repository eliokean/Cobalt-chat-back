"""
APPLICATION - DTO du module Crypt.
Les grands entiers circulent en chaînes décimales : un nombre JSON > 2^53
perd sa précision côté JavaScript.
"""
from typing import List

from pydantic import BaseModel, Field


class KeyGenInputDTO(BaseModel):
    bits: int = Field(512, ge=64, le=4096)


class KeyPairOutputDTO(BaseModel):
    e: str
    n: str
    d: str
    bits: int


class PublicKeyOutputDTO(BaseModel):
    e: str
    n: str
    bits: int
    fingerprint: str


class EncryptInputDTO(BaseModel):
    text: str = Field(..., max_length=10_000)
    e: str
    n: str


class EncryptOutputDTO(BaseModel):
    blocks: List[str]


class DecryptInputDTO(BaseModel):
    blocks: List[str]
    d: str
    n: str


class DecryptOutputDTO(BaseModel):
    text: str
