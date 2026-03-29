from __future__ import annotations

from abc import ABC, abstractmethod


class CaptchaSolver(ABC):
    @abstractmethod
    async def solve_turnstile(self, site_key: str, page_url: str) -> str:
        raise NotImplementedError
