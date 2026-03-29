from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode


def build_query(params: dict[str, Any]) -> str:
    cleaned = {k: v for k, v in params.items() if v is not None}
    return urlencode(cleaned, doseq=True)


@dataclass(slots=True)
class ResponseModel:
    data: dict[str, Any] = field(default_factory=dict)

    def __getattr__(self, name: str) -> Any:
        if name in self.data:
            return self.data[name]
        raise AttributeError(name)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.data)
