"""
Test unitaire pur sur le Domaine Chat
Zéro dépendance, zéro base de données, exécution en quelques millisecondes.
"""
import pytest
from datetime import datetime
from src.modules.chat.domain.models import Message
from src.modules.chat.domain.exceptions import EmptyMessageError, MessageTooLongError

def test_message_validation_success():
    msg = Message(
        id="test-1",
        chat_id="chat-1",
        sender_id="user-1",
        content="Salut le monde !",
        created_at=datetime.utcnow()
    )
    # Ne doit lever aucune exception
    msg.validate()
    assert msg.content == "Salut le monde !"

def test_message_validation_empty_fails():
    msg = Message(
        id="test-2",
        chat_id="chat-1",
        sender_id="user-1",
        content="   ",
        created_at=datetime.utcnow()
    )
    with pytest.raises(EmptyMessageError):
        msg.validate()
