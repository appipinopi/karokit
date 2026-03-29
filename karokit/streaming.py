from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, AsyncIterator, Awaitable, Callable

from .client.client import Client
from .errors import RealtimeConnectionError, RealtimeNotAvailableError

try:
    import socketio
except ImportError:
    socketio = None

EventHandler = Callable[[Any], Awaitable[None] | None]


class RealtimeStreamingClient:
    """
    Socket.IO based realtime stream helper for Karotter.
    """

    def __init__(
        self,
        client: Client,
        *,
        socket_url: str = "https://karotter.com",
        socket_path: str = "socket.io",
        transports: tuple[str, ...] = ("websocket",),
    ) -> None:
        self.client = client
        self.socket_url = socket_url.rstrip("/")
        self.socket_path = socket_path
        self.transports = transports
        self._sio: Any = None
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._registered_events: set[str] = set()

    def _ensure_socket_client(self) -> Any:
        if socketio is None:
            raise RealtimeNotAvailableError(
                "python-socketio is required for realtime streaming. "
                "Install with: pip install python-socketio[asyncio_client]"
            )
        if self._sio is None:
            self._sio = socketio.AsyncClient(
                reconnection=True,
                reconnection_attempts=0,
                reconnection_delay=1,
                reconnection_delay_max=10,
            )
        return self._sio

    def _register_event(self, event: str) -> None:
        sio = self._ensure_socket_client()
        if event in self._registered_events:
            return

        async def _dispatch(payload: Any) -> None:
            handlers = list(self._handlers.get(event, []))
            for handler in handlers:
                result = handler(payload)
                if asyncio.iscoroutine(result):
                    await result

        sio.on(event, _dispatch)
        self._registered_events.add(event)

    def on(self, event: str, handler: EventHandler) -> None:
        self._handlers[event].append(handler)
        if self._sio is not None:
            self._register_event(event)

    def off(self, event: str, handler: EventHandler) -> None:
        handlers = self._handlers.get(event)
        if not handlers:
            return
        self._handlers[event] = [item for item in handlers if item is not handler]

    @property
    def connected(self) -> bool:
        return bool(self._sio and self._sio.connected)

    async def connect(self) -> None:
        sio = self._ensure_socket_client()
        if sio.connected:
            return

        for event in list(self._handlers):
            self._register_event(event)

        try:
            await sio.connect(
                self.socket_url,
                headers=self.client.build_realtime_headers(),
                transports=list(self.transports),
                socketio_path=self.socket_path,
            )
        except Exception as exc:
            raise RealtimeConnectionError(f"Socket.IO connection failed: {exc}") from exc

    async def disconnect(self) -> None:
        if self._sio is None:
            return
        if self._sio.connected:
            await self._sio.disconnect()

    async def emit(self, event: str, payload: Any = None) -> None:
        await self.connect()
        await self._sio.emit(event, payload)

    async def notifications(self) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        def _enqueue(payload: Any) -> None:
            if isinstance(payload, dict):
                queue.put_nowait(payload)
            else:
                queue.put_nowait({"data": payload})

        self.on("notification", _enqueue)
        await self.connect()
        try:
            while True:
                yield await queue.get()
        finally:
            self.off("notification", _enqueue)

    async def dm_messages(self, group_id: int | str) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        payload = {"groupId": group_id}

        def _enqueue(payload: Any) -> None:
            if isinstance(payload, dict):
                queue.put_nowait(payload)
            else:
                queue.put_nowait({"data": payload})

        self.on("dd.newMessage", _enqueue)
        await self.connect()
        await self.emit("dd.join", payload)
        try:
            while True:
                yield await queue.get()
        finally:
            self.off("dd.newMessage", _enqueue)
            try:
                await self.emit("dd.leave", payload)
            except Exception:
                pass


class StreamingClient:
    def __init__(self, client: Client) -> None:
        self.client = client
        self.realtime = RealtimeStreamingClient(client)

    async def notifications(
        self,
        *,
        page: int = 1,
        limit: int = 15,
        continuous: bool = False,
        poll_interval: float = 10.0,
        realtime: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        if realtime:
            async for item in self.realtime.notifications():
                yield item
            return

        seen_ids: set[str] = set()
        current_page = page
        while True:
            data = await self.client.get_notifications(page=current_page, limit=limit)
            notifications = data.get("notifications", []) if isinstance(data, dict) else []
            if not notifications:
                if not continuous:
                    break
                await asyncio.sleep(poll_interval)
                current_page = page
                continue

            for item in reversed(notifications):
                notification_id = item.get("id") if isinstance(item, dict) else None
                if continuous and notification_id is not None:
                    key = str(notification_id)
                    if key in seen_ids:
                        continue
                    seen_ids.add(key)
                if isinstance(item, dict):
                    yield item

            if not continuous:
                current_page += 1
            else:
                await asyncio.sleep(poll_interval)
                current_page = page

    async def realtime_notifications(self) -> AsyncIterator[dict[str, Any]]:
        async for item in self.realtime.notifications():
            yield item

    async def realtime_dm_messages(self, group_id: int | str) -> AsyncIterator[dict[str, Any]]:
        async for item in self.realtime.dm_messages(group_id):
            yield item
