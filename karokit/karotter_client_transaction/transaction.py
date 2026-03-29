from __future__ import annotations

from .utils import stable_hash


class TransactionSigner:
    """
    Placeholder signer.
    Karotter does not currently require x-client-transaction signatures
    in the inspected web flow, but this class keeps twikit-like structure.
    """

    def sign(self, payload: str) -> str:
        return stable_hash(payload)
