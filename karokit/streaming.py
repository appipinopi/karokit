from __future__ import annotations

from typing import Any, AsyncIterator

from .client.client import Client


class StreamingClient:
    def __init__(self, client: Client) -> None:
        self.client = client

    async def notifications(self) -> AsyncIterator[dict[str, Any]]:
        page = 1
        while True:
            data = await self.client.get_notifications(page=page, limit=15)
            notifications = data.get("notifications", []) if isinstance(data, dict) else []
            if not notifications:
                break
            for item in notifications:
                yield item
            page += 1
