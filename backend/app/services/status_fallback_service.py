"""
File: status_fallback_service.py

Purpose:
    Implements the Status and Fallback Service for the PeaceHealth Rides
    Availability and Navigation Dashboard. This service determines which
    data source should be used by the system (live, cached, or sample),
    tracks feed availability, and generates system status information
    consumed by frontend status displays and warning banners.

System context:
    This service sits between the Ride Feed Collector and API endpoints.
    It evaluates available data sources, selects an appropriate fallback
    strategy when live data is unavailable, and produces the status
    information returned by the /api/status endpoint.

Creation date:
    May 2026

Initial author:
    Dacian Rapolla

Modification history:
    June 2026 - Dacian Rapolla - Implemented live/cache/sample fallback
    selection and frontend-facing system status generation.
"""

from __future__ import annotations

# Type hints are used throughout this service to clearly document the
# structure of status records and feed collections.
from typing import Any, Dict, List, Mapping, Optional, Sequence

# FeedCollectionError is raised when a feed source cannot be loaded.
# FeedStatus and SystemStatus are status models returned to API clients.
# RideFeedCollector performs the actual feed retrieval.
from backend.app.models.feed_models import FeedCollectionError
from backend.app.models.system_status import FeedStatus, SystemStatus
from backend.app.services.ride_feed_collector import RideFeedCollector


class StatusFallbackService:
    """
    Determines overall system health and selects the safest available data
    source. The service prefers live GBFS feeds, falls back to cached data
    when necessary, and finally uses sample data when no other source is
    available.
    """

    # Required feeds must be present for the dashboard to operate correctly.
    # These contain bike locations and station information.
    REQUIRED_FEEDS: Sequence[str] = (
        "free_bike_status",
        "station_information",
        "station_status",
    )

    # Optional feeds improve the user experience but are not required for
    # dashboard operation.
    OPTIONAL_FEEDS: Sequence[str] = ("system_alerts",)

    # Create a collector instance if one is not supplied. Dependency
    # injection allows unit tests to provide mock collectors.
    def __init__(self, collector: Optional[RideFeedCollector] = None) -> None:
        self.collector = collector or RideFeedCollector()

    # -------------------------------------------------------------------
    # Determine overall dashboard status.
    #
    # This method:
    #   1. Checks which sources are available.
    #   2. Selects the best source using fallback rules.
    #   3. Loads feeds from that source.
    #   4. Builds feed-level status records.
    #   5. Returns a frontend-friendly system status object.
    # -------------------------------------------------------------------
    def get_system_status(self) -> Dict[str, Any]:

        # Collect user-visible warning messages generated during status
        # evaluation.
        warnings: List[str] = []

        # Determine whether each supported source can currently provide data.
        live_feed_available = self._source_available("live")
        cache_data_available = self._source_available("cache")
        sample_data_available = self._source_available("sample")

        # Select the highest-priority source that is currently available.
        fallback_source = self.select_fallback_source(
            live_feed_available=live_feed_available,
            cache_data_available=cache_data_available,
            sample_data_available=sample_data_available,
        )

        # If no source can provide data, return an error status so the
        # frontend can inform the user.
        if fallback_source is None:
            status = SystemStatus(
                status="error",
                source="none",
                source_label="No Data Available",
                using_live_data=False,
                using_cached_data=False,
                using_sample_data=False,
                live_feed_available=False,
                cache_data_available=cache_data_available,
                sample_data_available=sample_data_available,
                last_successful_update=None,
                visible_message="No live, cached, or sample bike-share data is available.",
                feeds=[],
                warnings=["All data sources failed."],
            )
            return status.to_dict()

        # Attempt to load feeds from the selected source.
        # FeedCollectionError indicates the chosen source failed unexpectedly.
        try:
            raw_feeds = self.collector.load_dashboard_feeds(
                source=fallback_source,
                include_optional=True,
            )

        except FeedCollectionError as error:
            status = SystemStatus(
                status="error",
                source=fallback_source,
                source_label=self.label_data_source(fallback_source),
                using_live_data=False,
                using_cached_data=fallback_source == "cache",
                using_sample_data=fallback_source == "sample",
                live_feed_available=live_feed_available,
                cache_data_available=cache_data_available,
                sample_data_available=sample_data_available,
                last_successful_update=None,
                visible_message=f"Could not load {fallback_source} data.",
                feeds=[],
                warnings=[error.message],
            )
            return status.to_dict()

        # Inform users when the dashboard is operating in fallback mode.
        if fallback_source != "live":
            warnings.append(
                f"Live data is unavailable. Displaying {fallback_source} data."
            )

        # Build feed-level status records and determine the most recent update
        # timestamp available across all feeds.
        feed_statuses = self._build_feed_statuses(raw_feeds, fallback_source)
        last_successful_update = self._latest_timestamp(raw_feeds)

        # Build the final status object consumed by API clients and frontend
        # status displays.
        system_status = SystemStatus(
            status="ok" if fallback_source == "live" else "degraded",
            source=fallback_source,
            source_label=self.label_data_source(fallback_source),
            using_live_data=fallback_source == "live",
            using_cached_data=fallback_source == "cache",
            using_sample_data=fallback_source == "sample",
            live_feed_available=live_feed_available,
            cache_data_available=cache_data_available,
            sample_data_available=sample_data_available,
            last_successful_update=last_successful_update,
            visible_message=self._visible_message(fallback_source),
            feeds=feed_statuses,
            warnings=warnings,
        )

        return system_status.to_dict()

    # Create a standardized success record for feed collection events.
    def record_live_success(
        self,
        feed_name: str,
        timestamp: Optional[int] = None,
    ) -> Dict[str, Any]:
        return {
            "feed_name": feed_name,
            "success": True,
            "timestamp": timestamp,
            "message": "Live feed loaded successfully.",
        }

    # Create a standardized failure record for feed collection events.
    def record_feed_failure(self, feed_name: str, error: str) -> Dict[str, Any]:
        return {
            "feed_name": feed_name,
            "success": False,
            "error_message": error,
        }

    # Select the preferred source according to the fallback priority:
    #
    # live -> cache -> sample
    def select_fallback_source(
        self,
        live_feed_available: bool,
        cache_data_available: bool,
        sample_data_available: bool,
    ) -> Optional[str]:

        if live_feed_available:
            return "live"

        if cache_data_available:
            return "cache"

        if sample_data_available:
            return "sample"

        return None

    # Convert internal source identifiers into frontend-friendly labels.
    def label_data_source(self, source_type: str) -> str:
        labels = {
            "live": "Live Data",
            "cache": "Cached Data",
            "sample": "Sample Data",
        }

        return labels.get(source_type, "Unknown Data Source")

    # Test whether a source can successfully provide dashboard feeds.
    def _source_available(self, source: str) -> bool:
        try:
            self.collector.load_dashboard_feeds(
                source=source,
                include_optional=False,
            )
            return True

        except Exception:
            return False

    # Build FeedStatus records for all required and optional feeds.
    def _build_feed_statuses(
        self,
        raw_feeds: Mapping[str, Mapping[str, Any]],
        source_type: str,
    ) -> List[FeedStatus]:

        statuses: List[FeedStatus] = []

        for feed_name in (*self.REQUIRED_FEEDS, *self.OPTIONAL_FEEDS):

            raw_feed = raw_feeds.get(feed_name)

            # Create a status record describing availability and freshness
            # for the current feed.
            statuses.append(
                FeedStatus(
                    feed_name=feed_name,
                    available=raw_feed is not None,
                    source_type=source_type,
                    last_updated=self._read_last_updated(raw_feed),
                    error_message=None
                    if raw_feed is not None
                    else "Feed was not loaded.",
                )
            )

        return statuses

    # Determine the newest feed timestamp available across all loaded feeds.
    def _latest_timestamp(
        self,
        raw_feeds: Mapping[str, Mapping[str, Any]],
    ) -> Optional[int]:

        # Collect all valid timestamps found within the feed set.
        timestamps = [
            self._read_last_updated(raw_feed)
            for raw_feed in raw_feeds.values()
            if self._read_last_updated(raw_feed) is not None
        ]

        if not timestamps:
            return None

        return max(timestamps)

    # Safely extract a last_updated timestamp from a feed payload.
    def _read_last_updated(
        self,
        raw_feed: Optional[Mapping[str, Any]],
    ) -> Optional[int]:

        # Ignore malformed feed records.
        if not isinstance(raw_feed, Mapping):
            return None

        # Extract the raw timestamp value from the feed.
        value = raw_feed.get("last_updated")

        if isinstance(value, bool):
            return None

        if isinstance(value, (int, float)):
            return int(value)

        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())

        return None

    # Generate user-facing status text displayed by the frontend.
    def _visible_message(self, source: str) -> str:

        if source == "live":
            return "Displaying live PeaceHealth Rides availability data."

        if source == "cache":
            return (
                "Live data could not be refreshed. "
                "Displaying cached availability data."
            )

        if source == "sample":
            return (
                "Live data could not be loaded. "
                "Displaying sample data for demonstration."
            )

        return "Displaying unknown data source."
