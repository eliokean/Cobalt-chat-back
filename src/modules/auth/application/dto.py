"""
APPLICATION - DTO du module Auth
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RegisterInputDTO(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    display_name: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)
    role: str = Field("", max_length=64)


class LoginInputDTO(BaseModel):
    username: str
    password: str


class UserOutputDTO(BaseModel):
    id: str
    username: str
    display_name: str
    role: str = ""
    is_online: bool = False
    last_seen_at: Optional[datetime] = None

    @classmethod
    def from_domain(cls, user, is_online: bool = False) -> "UserOutputDTO":
        return cls(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
            is_online=is_online,
            last_seen_at=user.last_seen_at,
        )


class TokenOutputDTO(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOutputDTO
