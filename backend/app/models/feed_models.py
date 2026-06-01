"""Data models used by the ride feed collector."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


JSONDict = Dict[str, Any]


@dataclass(frozen=True)
class RawFeed:
    """Raw GBFS feed payload returned by the collector."""

    feed_name: str
    json_body: JSONDict
    retrieved_at: str
    source_type: str


@dataclass(frozen=True)
class CollectionStatus:
    """Status record for one feed collection attempt."""

    feed_name: str
    success: bool
    error_message: Optional[str]
    retrieved_at: str


class FeedCollectionError(RuntimeError):
    """Raised when a feed cannot be loaded or decoded."""

    def __init__(self, feed_name: str, source_type: str, message: str) -> None:
        self.feed_name = feed_name
        self.source_type = source_type
        self.message = message
        super().__init__(f"{source_type} feed {feed_name!r}: {message}")
