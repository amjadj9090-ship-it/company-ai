from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class CompanyAIRequest:
    """Canonical request envelope passed into Company AI orchestration."""

    message: str
    channel: str = "website"
    language: str | None = None
    context: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.message or not self.message.strip():
            raise ValueError("message must not be empty")
        if len(self.message) > 12000:
            raise ValueError("message exceeds the 12000 character limit")
        if not self.channel or not self.channel.strip():
            raise ValueError("channel must not be empty")

    def as_context(self) -> dict[str, Any]:
        return {
            "message": self.message.strip(),
            "channel": self.channel.strip(),
            "language": self.language,
            "context": dict(self.context or {}),
        }
