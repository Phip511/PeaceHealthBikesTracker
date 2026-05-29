"""Normalize raw GBFS feed documents into project-level data objects.

The normalizer is intentionally defensive. GBFS feeds can vary by version and
provider, so this module accepts both older v1/v2 field names and newer v3
vehicle/station field names where the project needs them.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, TypeAlias

from backend.app.models.normalized_models import (
    BikeLocation,
    FeedFreshness,
    HubLocation,
    NormalizationWarning,
    SystemAlert,
)


JSONMapping: TypeAlias = Mapping[str, Any]


class RideDataNormalizer:
    """Convert raw GBFS JSON dictionaries into stable project objects."""

    def __init__(self, source: str = "live") -> None:
        self.source = source
        self.warnings: List[NormalizationWarning] = []

    def normalize_bikes(self, raw_free_bike_status: JSONMapping) -> List[BikeLocation]:
        """Normalize `free_bike_status` or v3 `vehicle_status` records.

        Records with missing IDs or invalid coordinates are skipped and recorded
        as warnings. Availability is derived from common GBFS flags; if a feed
        does not expose any availability flags, a listed vehicle is considered
        available.
        """

        raw_feed = raw_free_bike_status if isinstance(raw_free_bike_status, Mapping) else {}
        bikes: List[BikeLocation] = []
        records = self._extract_records(raw_feed, ("bikes", "vehicles"))
        source_feed = self._source_feed_name(raw_feed, default="free_bike_status")
        feed_last_updated = self._timestamp_to_epoch(raw_feed.get("last_updated"))

        for index, record in enumerate(records):
            if not isinstance(record, Mapping):
                self._warn(source_feed, "Skipped non-object bike record.", str(index))
                continue

            bike_id = self._first_text(record, ("bike_id", "vehicle_id", "id"))
            record_id = bike_id or str(index)
            if not bike_id:
                self._warn(source_feed, "Skipped bike with missing ID.", record_id)
                continue

            coordinate = self._read_coordinate(record)
            if coordinate is None:
                self._warn(source_feed, "Skipped bike with invalid coordinates.", record_id)
                continue

            bikes.append(
                BikeLocation(
                    bike_id=bike_id,
                    latitude=coordinate[0],
                    longitude=coordinate[1],
                    is_available=self._bike_is_available(record),
                    last_reported=self._timestamp_to_epoch(record.get("last_reported")) or feed_last_updated,
                )
            )

        return bikes

    def normalize_hubs(
        self,
        raw_station_information: JSONMapping,
        raw_station_status: Optional[JSONMapping] = None,
    ) -> List[HubLocation]:
        """Normalize station information and optional station status feeds."""

        station_information_feed = raw_station_information if isinstance(raw_station_information, Mapping) else {}
        station_status_feed = raw_station_status if isinstance(raw_station_status, Mapping) else {}
        hubs: List[HubLocation] = []
        station_info_records = self._extract_records(station_information_feed, ("stations",))
        status_by_station_id = self._station_status_by_id(station_status_feed)
        feed_last_updated = self._timestamp_to_epoch(station_status_feed.get("last_updated"))

        for index, station_info in enumerate(station_info_records):
            if not isinstance(station_info, Mapping):
                self._warn("station_information", "Skipped non-object station record.", str(index))
                continue

            station_id = self._first_text(station_info, ("station_id", "id"))
            record_id = station_id or str(index)
            if not station_id:
                self._warn("station_information", "Skipped station with missing ID.", record_id)
                continue

            coordinate = self._read_coordinate(station_info)
            if coordinate is None:
                self._warn("station_information", "Skipped station with invalid coordinates.", record_id)
                continue

            station_status = status_by_station_id.get(station_id, {})
            name = self._first_text(station_info, ("name", "short_name")) or f"Station {station_id}"
            capacity = self._first_int(station_info, ("capacity",))
            if capacity is None:
                capacity = self._first_int(station_status, ("capacity",))

            hubs.append(
                HubLocation(
                    station_id=station_id,
                    name=name,
                    latitude=coordinate[0],
                    longitude=coordinate[1],
                    available_bikes=self._first_int(
                        station_status,
                        ("num_bikes_available", "num_vehicles_available"),
                    ),
                    capacity=capacity,
                    last_reported=self._timestamp_to_epoch(station_status.get("last_reported")) or feed_last_updated,
                )
            )

        return hubs

    def normalize_alerts(self, raw_system_alerts: JSONMapping) -> List[SystemAlert]:
        """Normalize public GBFS system alerts."""

        raw_feed = raw_system_alerts if isinstance(raw_system_alerts, Mapping) else {}
        alerts: List[SystemAlert] = []
        records = self._extract_records(raw_feed, ("alerts",))

        for index, record in enumerate(records):
            if not isinstance(record, Mapping):
                self._warn("system_alerts", "Skipped non-object alert record.", str(index))
                continue

            alert_id = self._first_text(record, ("alert_id", "id")) or str(index)
            times = record.get("times")
            start_time, end_time = self._read_alert_window(times)

            alerts.append(
                SystemAlert(
                    alert_id=alert_id,
                    summary=self._read_localized_text(record.get("summary")),
                    description=self._read_localized_text(record.get("description")),
                    affected_station_ids=self._affected_station_ids(record),
                    start_time=start_time,
                    end_time=end_time,
                )
            )

        return alerts

    def normalize_timestamp(self, raw_feed: JSONMapping) -> FeedFreshness:
        """Normalize feed-level freshness metadata."""

        feed = raw_feed if isinstance(raw_feed, Mapping) else {}
        last_updated = self._timestamp_to_epoch(feed.get("last_updated"))
        return FeedFreshness(
            source=self.source,
            last_updated=last_updated,
            is_live=self.source == "live",
            is_cached=self.source == "cache",
            is_sample=self.source == "sample",
        )

    def normalize_snapshot(self, raw_feeds: JSONMapping) -> Dict[str, Any]:
        """Normalize the common dashboard feed set into one response object."""

        self.warnings = []
        feed_snapshot = raw_feeds if isinstance(raw_feeds, Mapping) else {}

        bikes_feed = self._feed_from_snapshot(feed_snapshot, "free_bike_status", "vehicle_status")
        station_information = self._feed_from_snapshot(feed_snapshot, "station_information")
        station_status = self._feed_from_snapshot(feed_snapshot, "station_status")
        system_alerts = self._feed_from_snapshot(feed_snapshot, "system_alerts")

        freshness_feed = bikes_feed or station_status or station_information or system_alerts or {}

        return {
            "bikes": self.to_dicts(self.normalize_bikes(bikes_feed or {})),
            "hubs": self.to_dicts(self.normalize_hubs(station_information or {}, station_status or {})),
            "alerts": self.to_dicts(self.normalize_alerts(system_alerts or {})),
            "freshness": self.to_dict(self.normalize_timestamp(freshness_feed)),
            "warnings": self.to_dicts(self.warnings),
        }

    @staticmethod
    def to_dict(item: Any) -> Dict[str, Any]:
        """Convert a normalized dataclass object into a plain dictionary."""

        if is_dataclass(item):
            return asdict(item)
        if isinstance(item, Mapping):
            return dict(item)
        raise TypeError(f"Cannot convert {type(item).__name__} to dict.")

    @classmethod
    def to_dicts(cls, items: Iterable[Any]) -> List[Dict[str, Any]]:
        """Convert normalized dataclass objects into plain dictionaries."""

        return [cls.to_dict(item) for item in items]

    def _warn(self, feed_name: str, message: str, record_id: Optional[str] = None) -> None:
        self.warnings.append(NormalizationWarning(feed_name=feed_name, message=message, record_id=record_id))

    def _extract_records(self, raw_feed: JSONMapping, record_keys: Sequence[str]) -> List[Any]:
        if not isinstance(raw_feed, Mapping):
            return []

        data = raw_feed.get("data")
        if not isinstance(data, Mapping):
            return []

        for key in record_keys:
            records = data.get(key)
            if isinstance(records, list):
                return records

        # Some localized feeds wrap data under language keys such as "en".
        for value in data.values():
            if not isinstance(value, Mapping):
                continue
            for key in record_keys:
                records = value.get(key)
                if isinstance(records, list):
                    return records

        return []

    def _station_status_by_id(self, raw_station_status: JSONMapping) -> Dict[str, JSONMapping]:
        status_records = self._extract_records(raw_station_status, ("stations",))
        statuses: Dict[str, JSONMapping] = {}

        for index, status in enumerate(status_records):
            if not isinstance(status, Mapping):
                self._warn("station_status", "Skipped non-object station status record.", str(index))
                continue

            station_id = self._first_text(status, ("station_id", "id"))
            if not station_id:
                self._warn("station_status", "Skipped station status with missing ID.", str(index))
                continue

            statuses[station_id] = status

        return statuses

    def _read_coordinate(self, record: JSONMapping) -> Optional[Tuple[float, float]]:
        latitude = self._optional_float(record.get("lat", record.get("latitude")))
        longitude = self._optional_float(record.get("lon", record.get("longitude")))

        if latitude is None or longitude is None:
            return None

        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            return None

        return latitude, longitude

    def _bike_is_available(self, record: JSONMapping) -> bool:
        is_available = self._first_bool(record, ("is_available", "is_renting"))
        is_reserved = self._first_bool(record, ("is_reserved",))
        is_disabled = self._first_bool(record, ("is_disabled",))

        if is_available is False:
            return False
        if is_reserved is True or is_disabled is True:
            return False

        return True

    def _source_feed_name(self, raw_feed: JSONMapping, default: str) -> str:
        data = raw_feed.get("data") if isinstance(raw_feed, Mapping) else None
        if not isinstance(data, Mapping):
            return default
        if isinstance(data.get("vehicles"), list):
            return "vehicle_status"
        for value in data.values():
            if isinstance(value, Mapping) and isinstance(value.get("vehicles"), list):
                return "vehicle_status"
        return default

    def _feed_from_snapshot(self, raw_feeds: JSONMapping, *names: str) -> Optional[JSONMapping]:
        for name in names:
            feed = raw_feeds.get(name) if isinstance(raw_feeds, Mapping) else None
            if isinstance(feed, Mapping):
                return feed
        return None

    def _read_alert_window(self, times: Any) -> Tuple[Optional[int], Optional[int]]:
        if not isinstance(times, list) or not times:
            return None, None

        first_window = times[0]
        if not isinstance(first_window, Mapping):
            return None, None

        return (
            self._timestamp_to_epoch(first_window.get("start")),
            self._timestamp_to_epoch(first_window.get("end")),
        )

    def _read_localized_text(self, value: Any) -> str:
        if value is None:
            return ""

        if isinstance(value, str):
            return value

        if isinstance(value, list):
            for item in value:
                text = self._read_localized_text(item)
                if text:
                    return text
            return ""

        if isinstance(value, Mapping):
            if isinstance(value.get("text"), str):
                return value["text"]

            translations = value.get("translation")
            if isinstance(translations, list):
                for translation in translations:
                    if isinstance(translation, Mapping) and isinstance(translation.get("text"), str):
                        return translation["text"]

            for candidate in value.values():
                if isinstance(candidate, str):
                    return candidate

        return str(value)

    def _affected_station_ids(self, record: JSONMapping) -> List[str]:
        station_ids = self._string_list(record.get("station_ids"))
        if station_ids:
            return station_ids

        entities = record.get("informed_entities")
        if not isinstance(entities, list):
            return []

        affected_station_ids: List[str] = []
        for entity in entities:
            if not isinstance(entity, Mapping):
                continue
            station_id = self._optional_text(entity.get("station_id"))
            if station_id:
                affected_station_ids.append(station_id)

        return affected_station_ids

    def _first_text(self, record: JSONMapping, keys: Sequence[str]) -> Optional[str]:
        for key in keys:
            value = self._optional_text(record.get(key))
            if value:
                return value
        return None

    def _first_int(self, record: JSONMapping, keys: Sequence[str]) -> Optional[int]:
        for key in keys:
            value = self._optional_int(record.get(key))
            if value is not None:
                return value
        return None

    def _first_bool(self, record: JSONMapping, keys: Sequence[str]) -> Optional[bool]:
        for key in keys:
            value = self._optional_bool(record.get(key))
            if value is not None:
                return value
        return None

    def _string_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            text_values: List[str] = []
            for item in value:
                if item is None:
                    continue
                if isinstance(item, Mapping):
                    text = self._optional_text(item.get("text"))
                    if text:
                        text_values.append(text)
                    continue
                text_values.append(str(item))
            return text_values
        return []

    def _timestamp_to_epoch(self, value: Any) -> Optional[int]:
        if value is None or value == "":
            return None

        if isinstance(value, bool):
            return None

        if isinstance(value, (int, float)):
            return int(value)

        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            if stripped.isdigit():
                return int(stripped)

            try:
                parsed = datetime.fromisoformat(stripped.replace("Z", "+00:00"))
            except ValueError:
                return None

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return int(parsed.timestamp())

        return None

    def _timestamp_to_iso(self, epoch_seconds: Optional[int]) -> Optional[str]:
        if epoch_seconds is None:
            return None
        return datetime.fromtimestamp(epoch_seconds, timezone.utc).isoformat().replace("+00:00", "Z")

    def _optional_text(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _optional_int(self, value: Any) -> Optional[int]:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return int(value)
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _optional_float(self, value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _optional_bool(self, value: Any) -> Optional[bool]:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            if value == 1:
                return True
            if value == 0:
                return False
            return None
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "t", "yes", "y", "1"}:
                return True
            if lowered in {"false", "f", "no", "n", "0"}:
                return False
        return None


def normalize_bikes(raw_free_bike_status: JSONMapping) -> List[BikeLocation]:
    """Convenience wrapper for callers that do not need warning state."""

    return RideDataNormalizer().normalize_bikes(raw_free_bike_status)


def normalize_hubs(
    raw_station_information: JSONMapping,
    raw_station_status: Optional[JSONMapping] = None,
) -> List[HubLocation]:
    """Convenience wrapper for callers that do not need warning state."""

    return RideDataNormalizer().normalize_hubs(raw_station_information, raw_station_status)


def normalize_alerts(raw_system_alerts: JSONMapping) -> List[SystemAlert]:
    """Convenience wrapper for callers that do not need warning state."""

    return RideDataNormalizer().normalize_alerts(raw_system_alerts)


def normalize_timestamp(raw_feed: JSONMapping, source: str = "live") -> FeedFreshness:
    """Convenience wrapper for callers that only need freshness metadata."""

    return RideDataNormalizer(source=source).normalize_timestamp(raw_feed)


def normalize_snapshot(raw_feeds: JSONMapping, source: str = "live") -> Dict[str, Any]:
    """Convenience wrapper that returns plain dictionaries for API responses."""

    return RideDataNormalizer(source=source).normalize_snapshot(raw_feeds)
