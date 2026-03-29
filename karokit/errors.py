from __future__ import annotations

from typing import Any


class KarotterAPIError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
        url: str | None = None,
        payload: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.url = url
        self.payload = payload

    def __str__(self) -> str:
        base = super().__str__()
        parts = [base]
        if self.status_code is not None:
            parts.append(f"status={self.status_code}")
        if self.code:
            parts.append(f"code={self.code}")
        if self.url:
            parts.append(f"url={self.url}")
        return " | ".join(parts)


class PaidPlanRequiredError(KarotterAPIError):
    """Raised when endpoint returns a payment/subscription requirement."""


class RateLimitError(KarotterAPIError):
    """Raised when request is rate limited."""


__all__ = [
    "KarotterAPIError",
    "PaidPlanRequiredError",
    "RateLimitError",
]
