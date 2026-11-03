"""
CORE - Temps réel : gestionnaire de connexions WebSocket.

Les routes HTTP sont synchrones (exécutées dans un thread du pool) : elles
utilisent `notify()` qui planifie l'envoi sur la boucle asyncio principale.
"""
import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, Dict, Iterable, Optional, Set

from fastapi import WebSocket

log = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    # --- connexions --------------------------------------------------------

    async def connect(self, user_id: str, ws: WebSocket) -> bool:
        """Enregistre la socket. Retourne True si l'utilisateur vient de passer en ligne."""
        await ws.accept()
        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        was_offline = not self._connections.get(user_id)
        self._connections[user_id].add(ws)
        return was_offline

    def disconnect(self, user_id: str, ws: WebSocket) -> bool:
        """Retire la socket. Retourne True si l'utilisateur est désormais hors ligne."""
        conns = self._connections.get(user_id)
        if not conns:
            return False
        conns.discard(ws)
        if not conns:
            del self._connections[user_id]
            return True
        return False

    def is_online(self, user_id: str) -> bool:
        return bool(self._connections.get(user_id))

    def online_users(self) -> Set[str]:
        return set(self._connections)

    # --- envoi -------------------------------------------------------------

    async def send(self, user_ids: Iterable[str], event: Dict[str, Any]) -> None:
        data = json.dumps(event, default=str)
        for uid in set(user_ids):
            for ws in list(self._connections.get(uid, ())):
                try:
                    await ws.send_text(data)
                except Exception:  # socket morte : on la retire
                    self.disconnect(uid, ws)

    async def broadcast(self, event: Dict[str, Any]) -> None:
        await self.send(self.online_users(), event)

    def notify(self, user_ids: Iterable[str], event: Dict[str, Any]) -> None:
        """Envoi depuis du code synchrone (thread du pool)."""
        if self._loop is None or self._loop.is_closed():
            return
        user_ids = list(user_ids)
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is self._loop:
            self._loop.create_task(self.send(user_ids, event))
        else:
            asyncio.run_coroutine_threadsafe(self.send(user_ids, event), self._loop)


manager = ConnectionManager()
