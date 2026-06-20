"""Shared metadata for user-facing exception messages."""

from __future__ import annotations


class UserMessageMixin:
    """Attach a stable message code and format values to an exception."""

    def __init__(
        self,
        message: str,
        *,
        message_code: str | None = None,
        message_values: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message_code = message_code
        self.message_values = message_values or {}
