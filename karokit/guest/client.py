from __future__ import annotations

from ..client.client import Client


class GuestClient(Client):
    """
    Guest mode client.
    Karotter currently requires authenticated sessions for most endpoints.
    """

    async def login(self, *args, **kwargs):  # type: ignore[override]
        raise RuntimeError("GuestClient cannot login. Use Client instead.")
