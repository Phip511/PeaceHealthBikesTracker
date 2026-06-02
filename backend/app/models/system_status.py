"""
File: system_status.py

Purpose:
    Defines the status models used by the Status and Fallback Service.
    These models provide a standardized representation of overall system
    health, feed availability, data source information, and user-facing
    status messages.

System context:
    This file is part of the PeaceHealth Rides Availability and Navigation
    Dashboard backend. The StatusFallbackService constructs instances of
    these models and returns them through the /api/status endpoint and
    dashboard responses so the frontend can display data freshness,
    degraded mode warnings, and fallback status information.

Creation date:
    May 2026

Initial author:
    Dacian Rapolla

Modification history:
    June 2026 - Dacian Rapolla - Created status models for the
    Status/Fallback Service implementation.
"""

from __future__ import annotations

# dataclass is used to create lightweight data containers for status records.
# asdict is used to convert dataclass instances into dictionaries that can
# be returned directly by API endpoints.
from dataclasses import asdict, dataclass

# Type hints improve readability and help document expected data structures.
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# FeedStatus
# ---------------------------------------------------------------------------
# Represents the status of a single GBFS feed. The frontend can use this
# information to determine which feeds are available and when they were
# last updated.
# ---------------------------------------------------------------------------
@dataclass
class FeedStatus:
    # Name of the GBFS feed (free_bike_status, station_information, etc.).
    feed_name: str

    # True if the feed was successfully loaded.
    available: bool

    # Source used to obtain the feed (live, cache, or sample).
    source_type: str

    # Unix timestamp indicating the feed's most recent update time.
    # None indicates that no update timestamp was available.
    last_updated: Optional[int]

    # Optional error message explaining why a feed could not be loaded.
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# SystemStatus
# ---------------------------------------------------------------------------
# Represents the overall health and operational state of the dashboard.
# This model is returned by the Status/Fallback Service and consumed by
# frontend status displays and warning banners.
# ---------------------------------------------------------------------------
@dataclass
class SystemStatus:
    # Overall system state (ok, degraded, or error).
    status: str

    # Active source currently supplying dashboard data.
    source: str

    # Human-readable version of the source name.
    source_label: str

    # Indicates whether live PeaceHealth data is being used.
    using_live_data: bool

    # Indicates whether cached data is being used.
    using_cached_data: bool

    # Indicates whether sample/demo data is being used.
    using_sample_data: bool

    # True if live feeds are currently reachable.
    live_feed_available: bool

    # True if cached feed data exists and can be loaded.
    cache_data_available: bool

    # True if sample/demo data exists and can be loaded.
    sample_data_available: bool

    # Most recent successful feed update timestamp.
    last_successful_update: Optional[int]

    # User-facing message intended for display in the frontend.
    visible_message: str

    # Collection of feed-level status records.
    feeds: List[FeedStatus]

    # List of warnings generated while determining system status.
    warnings: List[str]

    # -----------------------------------------------------------------------
    # Convert the SystemStatus dataclass into a dictionary.
    #
    # FastAPI and frontend consumers work naturally with dictionaries and
    # JSON objects, so this helper simplifies serialization.
    # -----------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
