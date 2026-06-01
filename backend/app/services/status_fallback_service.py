from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from backend.app.models.feed_models import FeedCollectionError
from backend.app.models.system_status import FeedStatus, SystemStatus
from backend.app.services.ride_feed_collector import RideFeedCollector


class StatusFallbackService:
    """Tracks live/cache/sample status and chooses a safe fallback source."""

    REQUIRED_FEEDS: Sequence[str] = (
        "free_bike_status",
        "station_information",
        "station_status",
    )

    OPTIONAL_FEEDS: Sequence[str] = ("system_alerts",)

    def __init__(self, collector: Optional[RideFeedCollector] = None) -> None:
        self.collector = collector or RideFeedCollector()

    def get_system_status(self) -> Dict[str, Any]:
        warnings: List[str] = []

        live_feed_available = self._source_available("live")
        cache_data_available = self._source_available("cache")
        sample_data_available = self._source_available("sample")

        fallback_source = self.select_fallback_source(
            live_feed_available=live_feed_available,
            cache_data_available=cache_data_available,
            sample_data_available=sample_data_available,
        )

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

        if fallback_source != "live":
            warnings.append(f"Live data is unavailable. Displaying {fallback_source} data.")

        feed_statuses = self._build_feed_statuses(raw_feeds, fallback_source)
        last_successful_update = self._latest_timestamp(raw_feeds)

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

    def record_live_success(self, feed_name: str, timestamp: Optional[int] = None) -> Dict[str, Any]:
        return {
            "feed_name": feed_name,
            "success": True,
            "timestamp": timestamp,
            "message": "Live feed loaded successfully.",
        }

    def record_feed_failure(self, feed_name: str, error: str) -> Dict[str, Any]:
        return {
            "feed_name": feed_name,
            "success": False,
            "error_message": error,
        }

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

    def label_data_source(self, source_type: str) -> str:
        labels = {
            "live": "Live Data",
            "cache": "Cached Data",
            "sample": "Sample Data",
        }
        return labels.get(source_type, "Unknown Data Source")

    def _source_available(self, source: str) -> bool:
        try:
            self.collector.load_dashboard_feeds(source=source, include_optional=False)
            return True
        except Exception:
            return False

    def _build_feed_statuses(
        self,
        raw_feeds: Mapping[str, Mapping[str, Any]],
        source_type: str,
    ) -> List[FeedStatus]:
        statuses: List[FeedStatus] = []

        for feed_name in (*self.REQUIRED_FEEDS, *self.OPTIONAL_FEEDS):
            raw_feed = raw_feeds.get(feed_name)
            statuses.append(
                FeedStatus(
                    feed_name=feed_name,
                    available=raw_feed is not None,
                    source_type=source_type,
                    last_updated=self._read_last_updated(raw_feed),
                    error_message=None if raw_feed is not None else "Feed was not loaded.",
                )
            )

        return statuses

    def _latest_timestamp(self, raw_feeds: Mapping[str, Mapping[str, Any]]) -> Optional[int]:
        timestamps = [
            self._read_last_updated(raw_feed)
            for raw_feed in raw_feeds.values()
            if self._read_last_updated(raw_feed) is not None
        ]

        if not timestamps:
            return None

        return max(timestamps)

    def _read_last_updated(self, raw_feed: Optional[Mapping[str, Any]]) -> Optional[int]:
        if not isinstance(raw_feed, Mapping):
            return None

        value = raw_feed.get("last_updated")

        if isinstance(value, bool):
            return None

        if isinstance(value, (int, float)):
            return int(value)

        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())

        return None

    def _visible_message(self, source: str) -> str:
        if source == "live":
            return "Displaying live PeaceHealth Rides availability data."
        if source == "cache":
            return "Live data could not be refreshed. Displaying cached availability data."
        if source == "sample":
            return "Live data could not be loaded. Displaying sample data for demonstration."
        return "Displaying unknown data source."
