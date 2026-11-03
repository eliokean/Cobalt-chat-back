"""
APPLICATION - Data Transfer Objects (DTO)
Modèles de validation des entrées et sorties pour les Use Cases.
"""
from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from src.modules.auth.application.dto import UserOutputDTO


class SendMessageInputDTO(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    type: Literal["text"] = "text"


class ReactionInputDTO(BaseModel):
    emoji: str = Field(..., min_length=1, max_length=16)


class CreateDiscussionInputDTO(BaseModel):
    member_ids: List[str] = Field(..., min_length=1, max_length=50)
    title: Optional[str] = Field(None, max_length=64)
    is_group: Optional[bool] = None  # déduit si absent : groupe si titre ou >1 membre


class UpdateMembershipInputDTO(BaseModel):
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None


class ReactionOutputDTO(BaseModel):
    emoji: str
    count: int
    user_ids: List[str]


class MessageOutputDTO(BaseModel):
    id: str
    chat_id: str
    sender_id: str
    sender_name: Optional[str] = None
    content: str
    type: str
    created_at: datetime
    status: Literal["sent", "read"] = "sent"
    reactions: List[ReactionOutputDTO] = []
    ciphertext: Optional[str] = None  # renseigné seulement si include_cipher=true


class DiscussionOutputDTO(BaseModel):
    id: str
    title: str
    is_group: bool
    members: List[UserOutputDTO]
    is_pinned: bool
    is_archived: bool
    unread_count: int
    last_message: Optional[MessageOutputDTO] = None
    read_cursors: Dict[str, Optional[datetime]] = {}
    created_at: datetime
    updated_at: datetime
    key_fingerprint: Optional[str] = None
    key_bits: Optional[int] = None


class ReadReceiptOutputDTO(BaseModel):
    chat_id: str
    user_id: str
    read_at: datetime
