"""File: ride_feed_collector.py

Purpose:
    Retrieves raw GBFS JSON feed files for the PeaceHealth Rides Availability
    and Navigation Dashboard backend.

System context:
    This file implements the Ride Feed Collector module from the SDS. The
    collector sits between the Dashboard API and external/local GBFS data
    sources. It does not interpret bike, hub, or alert fields. Its job is to
    load JSON, label where that JSON came from, record collection status, and
    return raw feed objects to the Ride Data Normalizer.

Creation date:
    May 27, 2026

Initial author:
    Drew Moulton

Modification history:
    May 28, 2026 - Drew Moulton - Implemented live, sample, and cache feed
    collection.
    May 28, 2026 - Drew Moulton - Refactored feed models and constants into
    separate modules.
    May 28, 2026 - Drew Moulton - Added detailed inline comments for CS 422
    code-commenting expectations.
"""

from __future__ import annotations

# json is used to decode sample/cache files and live HTTP response bodies.
import json

# os is used to read environment variables such as APP_MODE and the GBFS URL.
import os

# datetime and timezone are used to timestamp every collected RawFeed/status.
from datetime import datetime, timezone

# Path is used for platform-independent sample and cache file paths.
from pathlib import Path

# Typing imports document the structure of dictionaries, optional settings, and
# feed-name sequences used throughout this module.
from typing import Any, Dict, List, Mapping, Optional, Sequence

# urllib is used instead of a third-party HTTP library so the collector has no
# external dependency before FastAPI or other backend dependencies are added.
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

# Feed constants keep default settings out of the service logic.
from backend.app.constants.feed_constants import DEFAULT_FEED_TIMEOUT_SECONDS, DEFAULT_GBFS_AUTO_DISCOVERY_URL

# Feed models define the data objects shown in the SDS static model.
from backend.app.models.feed_models import CollectionStatus, FeedCollectionError, JSONDict, RawFeed


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    """Return the current time in a compact UTC ISO-8601 string."""

    # datetime.now(timezone.utc) makes the timestamp explicit and portable
    # instead of relying on the evaluator machine's local timezone.
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_feed_name(feed_name: str) -> str:
    """Normalize user-provided or GBFS-provided feed names."""

    # normalized_name is the canonical form used for dictionary keys and local
    # filenames. It removes surrounding whitespace and lowercases the name.
    normalized_name = str(feed_name).strip().lower()

    # Feed names sometimes arrive as filenames. The collector stores names
    # without the .json suffix so callers can use either form.
    if normalized_name.endswith(".json"):
        normalized_name = normalized_name[:-5]

    # An empty feed name cannot map to a real GBFS file, so fail early with a
    # programmer-facing ValueError instead of creating a confusing path.
    if not normalized_name:
        raise ValueError("feed_name must not be empty.")

    # The returned value is safe to use as a feed dictionary key or JSON file
    # stem in the local sample/cache directories.
    return normalized_name


# ---------------------------------------------------------------------------
# Local Sample and Cache Store
# ---------------------------------------------------------------------------


class LocalDemonstrationDataStore:
    """Read sample/cache feed files and write cache files for demo fallback."""

    def __init__(
        self,
        sample_dir: Path | str,
        cache_dir: Path | str,
    ) -> None:
        # sample_dir points to committed JSON files used for demo/sample mode.
        self.sample_dir = Path(sample_dir)

        # cache_dir points to generated JSON files from the last successful live
        # requests. This directory may be empty on a fresh install.
        self.cache_dir = Path(cache_dir)

    def read_sample(self, feed_name: str) -> RawFeed:
        """Read one feed from the local sample-data directory."""

        # normalized_name gives the file stem used by _read_feed_file.
        normalized_name = _normalize_feed_name(feed_name)

        # All sample files are labeled with source_type="sample" so the status
        # and normalizer layers can tell users the data is not live.
        return self._read_feed_file(self.sample_dir, normalized_name, "sample")

    def read_cache(self, feed_name: str) -> RawFeed:
        """Read one feed from the local cache directory."""

        # normalized_name gives the file stem used by _read_feed_file.
        normalized_name = _normalize_feed_name(feed_name)

        # Cached files are labeled separately from samples because cached data
        # may be real but stale.
        return self._read_feed_file(self.cache_dir, normalized_name, "cache")

    def write_cache(self, feed_name: str, json_body: Mapping[str, Any]) -> Path:
        """Write one raw feed JSON object to the local cache directory."""

        # normalized_name determines the cache filename and keeps cache naming
        # consistent with sample naming.
        normalized_name = _normalize_feed_name(feed_name)

        # The cache directory may not exist until the first successful live
        # request, so it is created immediately before writing.
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # path is the full cache JSON path, such as cache/free_bike_status.json.
        path = self._feed_path(self.cache_dir, normalized_name)

        # The JSON file is written with stable formatting so cache contents are
        # readable during debugging and deterministic if inspected in tests.
        with path.open("w", encoding="utf-8") as file:
            json.dump(json_body, file, indent=2, sort_keys=True)
            file.write("\n")

        # The caller receives the path so tests or status tools can confirm
        # which cache file was updated.
        return path

    def cache_exists(self, feed_name: str) -> bool:
        """Return whether a cached feed file exists and is non-empty."""

        # path is the expected cache file for the requested feed.
        path = self._feed_path(self.cache_dir, _normalize_feed_name(feed_name))

        # A zero-byte file is treated as unusable because json.load would fail.
        return path.exists() and path.stat().st_size > 0

    def _read_feed_file(self, directory: Path, feed_name: str, source_type: str) -> RawFeed:
        """Read, validate, and wrap one local feed JSON file."""

        # path is the concrete JSON file to load from the selected directory.
        path = self._feed_path(directory, feed_name)

        # Missing files become FeedCollectionError so caller code can report a
        # collection failure using the same type for sample, cache, and live.
        if not path.exists():
            raise FeedCollectionError(feed_name, source_type, f"File does not exist: {path}.")

        # This block opens and parses the JSON file. JSON errors and OS errors
        # are converted into readable feed-collection errors.
        try:
            with path.open("r", encoding="utf-8") as file:
                decoded = json.load(file)
        except json.JSONDecodeError as error:
            raise FeedCollectionError(feed_name, source_type, f"File is not valid JSON: {error.msg}.") from error
        except OSError as error:
            raise FeedCollectionError(feed_name, source_type, f"Could not read file: {error}.") from error

        # GBFS feed files are JSON objects at the root. A list/string root would
        # be malformed for the downstream normalizer.
        if not isinstance(decoded, dict):
            raise FeedCollectionError(feed_name, source_type, "File JSON root must be an object.")

        # RawFeed preserves the JSON body and adds source/timestamp metadata
        # without interpreting the feed contents.
        return RawFeed(
            feed_name=feed_name,
            json_body=decoded,
            retrieved_at=_utc_now_iso(),
            source_type=source_type,
        )

    def _feed_path(self, directory: Path, feed_name: str) -> Path:
        """Build the path for a local sample or cache feed file."""

        # Local feed files are named with the normalized feed name plus .json.
        return directory / f"{feed_name}.json"


# ---------------------------------------------------------------------------
# Ride Feed Collector Service
# ---------------------------------------------------------------------------


class RideFeedCollector:
    """Load raw GBFS feeds for the backend services."""

    def __init__(
        self,
        mode: Optional[str] = None,
        feed_index_url: Optional[str] = None,
        auto_discovery_url: Optional[str] = None,
        sample_dir: Optional[Path | str] = None,
        cache_dir: Optional[Path | str] = None,
        timeout_seconds: float = DEFAULT_FEED_TIMEOUT_SECONDS,
    ) -> None:
        # app_dir is the backend/app directory. It is used to build default
        # sample and cache paths when tests or API code do not inject paths.
        app_dir = Path(__file__).resolve().parents[1]

        # mode controls the default data source for requests: live, sample, or
        # cache. APP_MODE lets Docker or a local shell override the default.
        self.mode = (mode or os.getenv("APP_MODE") or "live").strip().lower()

        # feed_index_url is the GBFS auto-discovery URL. auto_discovery_url is
        # kept as a constructor alias because the README and SDS use that term.
        self.feed_index_url = (
            feed_index_url
            or auto_discovery_url
            or os.getenv("GBFS_AUTO_DISCOVERY_URL")
            or DEFAULT_GBFS_AUTO_DISCOVERY_URL
        )

        # timeout_seconds limits live HTTP requests so a bad network response
        # does not hang the backend indefinitely.
        self.timeout_seconds = timeout_seconds

        # local_data_store owns local file reads/writes, keeping filesystem
        # details separate from feed-selection logic.
        self.local_data_store = LocalDemonstrationDataStore(
            sample_dir=sample_dir if sample_dir is not None else app_dir / "data" / "sample",
            cache_dir=cache_dir if cache_dir is not None else app_dir / "data" / "cache",
        )

        # _feed_index caches the live gbfs.json response for the life of this
        # collector instance so repeated feed requests do not refetch it.
        self._feed_index: Optional[RawFeed] = None

        # _feed_urls caches the feed-name-to-URL mapping extracted from gbfs.json.
        self._feed_urls: Optional[Dict[str, str]] = None

        # _collection_status stores a chronological record of collection
        # successes and failures for a future status endpoint or status panel.
        self._collection_status: List[CollectionStatus] = []

    @property
    def auto_discovery_url(self) -> str:
        """Backward-compatible alias for the configured GBFS index URL."""

        # This alias keeps older caller code working while the internal name
        # uses the shorter feed_index_url.
        return self.feed_index_url

    @property
    def sample_dir(self) -> Path:
        """Return the configured sample-data directory."""

        # Expose the path through the collector for tests and status reporting.
        return self.local_data_store.sample_dir

    @property
    def cache_dir(self) -> Path:
        """Return the configured cache directory."""

        # Expose the path through the collector for tests and status reporting.
        return self.local_data_store.cache_dir

    def get_feed_index(self, source: Optional[str] = None) -> RawFeed:
        """Return the GBFS auto-discovery feed as a RawFeed."""

        # selected_source is the explicit source argument or this collector's
        # configured mode, normalized to live/sample/cache.
        selected_source = self._source_or_mode(source)

        # Sample mode reads gbfs.json from committed demo data.
        if selected_source == "sample":
            return self.get_sample_feed_file("gbfs")

        # Cache mode reads gbfs.json from the generated cache directory.
        if selected_source == "cache":
            return self.get_cached_feed_file("gbfs")

        # A previously fetched live index is reused to avoid duplicate network
        # requests and to keep URL resolution consistent within one collector.
        if self._feed_index is not None:
            return self._feed_index

        # Live mode fetches the auto-discovery feed and records any failure in
        # collection status before re-raising the error.
        try:
            raw_feed = self._fetch_json(self.feed_index_url, "gbfs")
        except FeedCollectionError as error:
            self._record_status("gbfs", False, error.message)
            raise

        # A successful live index is cached in memory and on disk for possible
        # fallback use later.
        self._feed_index = raw_feed
        self.local_data_store.write_cache("gbfs", raw_feed.json_body)
        self._record_status("gbfs", True)

        # The caller receives the unmodified GBFS index plus source metadata.
        return raw_feed

    def get_feed_file(self, feed_name: str, source: Optional[str] = None) -> RawFeed:
        """Return one raw GBFS feed by name as a RawFeed."""

        # normalized_name lets callers pass either "station_status" or
        # "station_status.json" and get the same feed.
        normalized_name = _normalize_feed_name(feed_name)

        # selected_source decides whether the feed comes from live HTTP, sample
        # files, or cached files.
        selected_source = self._source_or_mode(source)

        # Sample mode delegates all file handling to the local data store.
        if selected_source == "sample":
            return self.get_sample_feed_file(normalized_name)

        # Cache mode also delegates all file handling to the local data store.
        if selected_source == "cache":
            return self.get_cached_feed_file(normalized_name)

        # Live mode first resolves the requested feed name through gbfs.json.
        feed_url = self.get_feed_urls().get(normalized_name)

        # If gbfs.json does not advertise the requested feed, the collector
        # records a readable failure instead of attempting a guessed URL.
        if feed_url is None:
            message = "Feed is not listed in gbfs.json."
            self._record_status(normalized_name, False, message)
            raise FeedCollectionError(normalized_name, "live", message)

        # This block fetches the live feed and records failed network/JSON
        # outcomes before re-raising the failure to the caller.
        try:
            raw_feed = self._fetch_json(feed_url, normalized_name)
        except FeedCollectionError as error:
            self._record_status(normalized_name, False, error.message)
            raise

        # Successful live feeds are written to cache before returning.
        self.local_data_store.write_cache(normalized_name, raw_feed.json_body)
        self._record_status(normalized_name, True)

        # The RawFeed contains the original JSON body plus source/timestamp data.
        return raw_feed

    def get_sample_feed_file(self, feed_name: str) -> RawFeed:
        """Load one sample feed JSON file."""

        # normalized_name is the sample filename stem.
        normalized_name = _normalize_feed_name(feed_name)

        # This block reads the local sample feed and records failed file/JSON
        # outcomes before re-raising the failure.
        try:
            raw_feed = self.local_data_store.read_sample(normalized_name)
        except FeedCollectionError as error:
            self._record_status(normalized_name, False, error.message)
            raise

        # Successful sample reads are recorded just like live reads.
        self._record_status(normalized_name, True)
        return raw_feed

    def get_cached_feed_file(self, feed_name: str) -> RawFeed:
        """Load one cached feed JSON file."""

        # normalized_name is the cache filename stem.
        normalized_name = _normalize_feed_name(feed_name)

        # This block reads the local cached feed and records failed file/JSON
        # outcomes before re-raising the failure.
        try:
            raw_feed = self.local_data_store.read_cache(normalized_name)
        except FeedCollectionError as error:
            self._record_status(normalized_name, False, error.message)
            raise

        # Successful cache reads are recorded separately from sample/live reads
        # because the RawFeed source_type stays "cache".
        self._record_status(normalized_name, True)
        return raw_feed

    def get_feed_urls(self, source: Optional[str] = None) -> Dict[str, str]:
        """Return a mapping of GBFS feed names to their discovered URLs."""

        # selected_source determines whether gbfs.json is read from live,
        # sample, or cache before URL extraction.
        selected_source = self._source_or_mode(source)

        # Live URL mappings are cached after the first successful extraction.
        if selected_source == "live" and self._feed_urls is not None:
            return dict(self._feed_urls)

        # feed_index is the raw gbfs.json feed from the selected source.
        feed_index = self.get_feed_index(source=selected_source)

        # feed_urls maps names such as "station_status" to absolute URLs.
        feed_urls = self._extract_feed_urls(feed_index.json_body, selected_source)

        # Only live mappings are cached because sample/cache reads are cheap and
        # may be changed by tests between collector instances.
        if selected_source == "live":
            self._feed_urls = feed_urls

        return feed_urls

    def load_dashboard_feeds(
        self,
        source: Optional[str] = None,
        include_optional: bool = True,
    ) -> Dict[str, JSONDict]:
        """Load the common dashboard feeds as raw JSON dictionaries."""

        # selected_source applies the caller's source choice to every feed in
        # this dashboard load operation.
        selected_source = self._source_or_mode(source)

        # raw_feeds is the API-friendly dictionary passed to normalize_snapshot.
        raw_feeds: Dict[str, JSONDict] = {}

        # PeaceHealth/GBFS deployments may expose either free_bike_status or the
        # newer vehicle_status. The first available one is used.
        vehicle_feed = self._first_available_feed(
            ("free_bike_status", "vehicle_status"),
            selected_source,
            required=True,
        )

        # The vehicle feed is stored under its actual feed name so the normalizer
        # can detect whether it received free_bike_status or vehicle_status.
        raw_feeds[vehicle_feed.feed_name] = vehicle_feed.json_body

        # Station information and station status are required for hub display.
        for feed_name in ("station_information", "station_status"):
            raw_feed = self.get_feed_file(feed_name, source=selected_source)
            raw_feeds[raw_feed.feed_name] = raw_feed.json_body

        # System alerts are optional because not every GBFS deployment provides
        # them. Missing alerts should not block bike/hub display.
        if include_optional:
            try:
                raw_feed = self.get_feed_file("system_alerts", source=selected_source)
            except FeedCollectionError:
                pass
            else:
                raw_feeds[raw_feed.feed_name] = raw_feed.json_body

        # The returned dictionary intentionally contains raw JSON, not RawFeed
        # objects, because the normalizer only needs the payloads.
        return raw_feeds

    def write_cache(self, feed_name: str, raw_json: Mapping[str, Any]) -> Path:
        """Write a raw feed JSON object to the local cache directory."""

        # This wrapper keeps cache writes available through the collector while
        # the LocalDemonstrationDataStore owns the filesystem details.
        return self.local_data_store.write_cache(feed_name, raw_json)

    def cache_exists(self, feed_name: str) -> bool:
        """Return whether a cached feed file exists and is non-empty."""

        # This wrapper is used by tests and can later support status endpoints.
        return self.local_data_store.cache_exists(feed_name)

    def get_collection_status(self) -> List[CollectionStatus]:
        """Return recorded feed collection statuses."""

        # Return a copy so callers cannot accidentally mutate internal status
        # history.
        return list(self._collection_status)

    def _first_available_feed(
        self,
        feed_names: Sequence[str],
        source: str,
        required: bool,
    ) -> RawFeed:
        """Return the first feed in a candidate list that can be loaded."""

        # last_error preserves the most recent failure so a required feed can
        # raise a useful error if every candidate fails.
        last_error: Optional[FeedCollectionError] = None

        # Try candidate feeds in order. This supports GBFS version differences
        # without making callers know every possible vehicle feed name.
        for feed_name in feed_names:
            try:
                return self.get_feed_file(feed_name, source=source)
            except FeedCollectionError as error:
                last_error = error

        # Required candidate groups fail loudly when no candidate can be loaded.
        if required:
            names = ", ".join(feed_names)
            message = last_error.message if last_error else "No candidate feeds were provided."
            raise FeedCollectionError(names, source, message)

        # Optional candidate groups can return an empty RawFeed placeholder.
        return RawFeed(
            feed_name=_normalize_feed_name(feed_names[0]),
            json_body={},
            retrieved_at=_utc_now_iso(),
            source_type=source,
        )

    def _fetch_json(self, url: str, feed_name: str) -> RawFeed:
        """Fetch one live GBFS JSON feed and wrap it in RawFeed."""

        # request sets a JSON Accept header and a project User-Agent so the
        # public feed can identify the client if needed.
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "PeaceHealthBikesTracker/1.0"})

        # This block performs the HTTP request and converts network-style errors
        # into FeedCollectionError so callers use one error type.
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                body = response.read().decode(charset)
        except HTTPError as error:
            raise FeedCollectionError(feed_name, "live", f"HTTP {error.code} while requesting {url}.") from error
        except URLError as error:
            raise FeedCollectionError(feed_name, "live", f"Network error while requesting {url}: {error.reason}.") from error
        except TimeoutError as error:
            message = f"Timed out after {self.timeout_seconds:g} seconds while requesting {url}."
            raise FeedCollectionError(feed_name, "live", message) from error

        # This block decodes the response body as JSON and reports invalid JSON
        # with a readable message.
        try:
            decoded = json.loads(body)
        except json.JSONDecodeError as error:
            raise FeedCollectionError(feed_name, "live", f"Response was not valid JSON: {error.msg}.") from error

        # GBFS feed files should be JSON objects. Other JSON roots are rejected
        # before they reach the normalizer.
        if not isinstance(decoded, dict):
            raise FeedCollectionError(feed_name, "live", "Response JSON root must be an object.")

        # RawFeed labels the live payload without changing its GBFS structure.
        return RawFeed(
            feed_name=_normalize_feed_name(feed_name),
            json_body=decoded,
            retrieved_at=_utc_now_iso(),
            source_type="live",
        )

    def _extract_feed_urls(self, feed_index: Mapping[str, Any], source_type: str) -> Dict[str, str]:
        """Extract feed-name-to-URL mappings from gbfs.json."""

        # data is the GBFS index body. Some feeds use data.feeds, and some use
        # localized wrappers such as data.en.feeds.
        data = feed_index.get("data")

        # Without a data object, gbfs.json cannot be used to discover feeds.
        if not isinstance(data, Mapping):
            raise FeedCollectionError("gbfs", source_type, "gbfs.json is missing a data object.")

        # feed_urls accumulates normalized feed names mapped to absolute URLs.
        feed_urls: Dict[str, str] = {}

        # Some GBFS feeds list feeds directly at data.feeds.
        direct_feeds = data.get("feeds")
        if isinstance(direct_feeds, list):
            feed_urls.update(self._feed_urls_from_records(direct_feeds))

        # Other GBFS feeds wrap feed lists by language, such as data.en.feeds.
        for value in data.values():
            if not isinstance(value, Mapping):
                continue
            localized_feeds = value.get("feeds")
            if isinstance(localized_feeds, list):
                feed_urls.update(self._feed_urls_from_records(localized_feeds))

        # An empty mapping means the feed index did not contain usable feed
        # records, so live/sample/cache collection cannot continue.
        if not feed_urls:
            raise FeedCollectionError("gbfs", source_type, "gbfs.json does not list any feeds.")

        return feed_urls

    def _feed_urls_from_records(self, feeds: Sequence[Any]) -> Dict[str, str]:
        """Convert GBFS feed records into a feed-name-to-URL dictionary."""

        # feed_urls stores only valid feed records. Invalid records are ignored
        # because a GBFS index may include unexpected entries.
        feed_urls: Dict[str, str] = {}

        # Each feed record should include a name and a URL.
        for feed in feeds:
            if not isinstance(feed, Mapping):
                continue

            # name is the GBFS feed name, such as free_bike_status.
            name = feed.get("name")

            # url is the feed location. It may be absolute or relative.
            url = feed.get("url")

            # Records missing usable name/URL values cannot be fetched.
            if not isinstance(name, str) or not isinstance(url, str):
                continue

            # urljoin converts relative feed URLs into absolute URLs based on
            # the configured gbfs.json location.
            feed_urls[_normalize_feed_name(name)] = urljoin(self.feed_index_url, url)

        return feed_urls

    def _source_or_mode(self, source: Optional[str]) -> str:
        """Resolve a caller-provided source or collector mode."""

        # selected_source is the source argument if provided, otherwise this
        # collector's mode, otherwise live as the final default.
        selected_source = (source or self.mode or "live").strip().lower()

        # Demo terminology maps to sample mode because both use committed local
        # JSON files.
        if selected_source in {"demo", "demonstration"}:
            return "sample"

        # Only these source names are supported by the collector.
        if selected_source not in {"live", "sample", "cache"}:
            raise ValueError(f"Unsupported feed source: {selected_source!r}")

        return selected_source

    def _record_status(
        self,
        feed_name: str,
        success: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """Append one collection status record to the collector history."""

        # CollectionStatus is intentionally small so it can be surfaced later by
        # a status endpoint or frontend status panel.
        self._collection_status.append(
            CollectionStatus(
                feed_name=_normalize_feed_name(feed_name),
                success=success,
                error_message=error_message,
                retrieved_at=_utc_now_iso(),
            )
        )
