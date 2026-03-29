from __future__ import annotations

from .base import CaptchaSolver


class Capsolver(CaptchaSolver):
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    async def solve_turnstile(self, site_key: str, page_url: str) -> str:
        if not self.api_key:
            raise RuntimeError("Capsolver api_key is not configured.")
        raise NotImplementedError(
            "Capsolver integration point is ready but the provider API call is not implemented yet."
        )
