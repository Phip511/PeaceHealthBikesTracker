"""Data models produced by the ride data normalizer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class NormalizationWarning:
    """A non-fatal problem found while normalizing one feed or record."""

    feed_name: str
    message: str
    record_id: Optional[str] = None


@dataclass(frozen=True)
class FeedFreshness:
    """Timestamp and source metadata shared by normalized responses."""

    source: str
    last_updated: Optional[int]
    is_live: bool
    is_cached: bool
    is_sample: bool


@dataclass(frozen=True)
class BikeLocation:
    """Simplified vehicle location used by the dashboard and nearby queries."""

    bike_id: str
    latitude: float
    longitude: float
    is_available: bool
    last_reported: Optional[int] = None


@dataclass(frozen=True)
class HubLocation:
    """Simplified station/hub location with optional live availability."""

    station_id: str
    name: str
    latitude: float
    longitude: float
    available_bikes: Optional[int] = None
    capacity: Optional[int] = None
    last_reported: Optional[int] = None


@dataclass(frozen=True)
class SystemAlert:
    """Simplified public service alert."""

    alert_id: str
    summary: str
    description: str
    affected_station_ids: List[str]
    start_time: Optional[int] = None
    end_time: Optional[int] = None
