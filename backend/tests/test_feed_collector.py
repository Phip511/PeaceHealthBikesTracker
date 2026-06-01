import json
import tempfile
import unittest
from pathlib import Path

from backend.app.models.feed_models import CollectionStatus, FeedCollectionError, RawFeed
from backend.app.services.ride_feed_collector import (
    LocalDemonstrationDataStore,
    RideFeedCollector,
)
from backend.tests.fixtures.gbfs_samples import (
    sample_free_bike_status,
    sample_gbfs_index,
    sample_station_information,
    sample_station_status,
    sample_system_alerts,
)


class FakeLiveRideFeedCollector(RideFeedCollector):
    def __init__(self, sample_dir: Path, cache_dir: Path) -> None:
        super().__init__(
            mode="live",
            feed_index_url="https://example.test/gbfs.json",
            sample_dir=sample_dir,
            cache_dir=cache_dir,
        )
        self.requested_urls = []

    def _fetch_json(self, url: str, feed_name: str) -> RawFeed:
        self.requested_urls.append((url, feed_name))

        if feed_name == "gbfs":
            return RawFeed(
                feed_name="gbfs",
                json_body=sample_gbfs_index(),
                retrieved_at="2026-05-29T12:00:00Z",
                source_type="live",
            )

        return RawFeed(
            feed_name=feed_name,
            json_body={"data": {}},
            retrieved_at="2026-05-29T12:00:00Z",
            source_type="live",
        )


class RideFeedCollectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sample_tmp = tempfile.TemporaryDirectory()
        self.cache_tmp = tempfile.TemporaryDirectory()
        self.sample_dir = Path(self.sample_tmp.name)
        self.cache_dir = Path(self.cache_tmp.name)
        self._write_sample_files()

    def tearDown(self) -> None:
        self.sample_tmp.cleanup()
        self.cache_tmp.cleanup()

    def test_local_data_store_reads_sample_as_raw_feed(self) -> None:
        data_store = LocalDemonstrationDataStore(self.sample_dir, self.cache_dir)

        raw_feed = data_store.read_sample("free_bike_status")

        self.assertIsInstance(raw_feed, RawFeed)
        self.assertEqual(raw_feed.feed_name, "free_bike_status")
        self.assertEqual(raw_feed.source_type, "sample")
        self.assertEqual(raw_feed.json_body["data"]["bikes"][0]["bike_id"], "bike-1")

    def test_sample_collector_loads_dashboard_feeds(self) -> None:
        collector = RideFeedCollector(
            mode="sample",
            feed_index_url="https://example.test/gbfs.json",
            sample_dir=self.sample_dir,
            cache_dir=self.cache_dir,
        )

        raw_feeds = collector.load_dashboard_feeds()

        self.assertEqual(
            set(raw_feeds),
            {"free_bike_status", "station_information", "station_status", "system_alerts"},
        )
        self.assertEqual(raw_feeds["free_bike_status"]["data"]["bikes"][0]["bike_id"], "bike-1")
        self.assertTrue(all(isinstance(status, CollectionStatus) for status in collector.get_collection_status()))

    def test_feed_urls_are_extracted_from_localized_gbfs_index(self) -> None:
        collector = RideFeedCollector(
            mode="sample",
            feed_index_url="https://example.test/gbfs.json",
            sample_dir=self.sample_dir,
            cache_dir=self.cache_dir,
        )

        feed_urls = collector.get_feed_urls()

        self.assertEqual(feed_urls["free_bike_status"], "https://example.test/free_bike_status.json")
        self.assertEqual(feed_urls["station_information"], "https://example.test/station_information.json")

    def test_cache_round_trip_uses_local_data_store(self) -> None:
        data_store = LocalDemonstrationDataStore(self.sample_dir, self.cache_dir)

        data_store.write_cache("free_bike_status", {"data": {"bikes": []}})
        raw_feed = data_store.read_cache("free_bike_status")

        self.assertTrue(data_store.cache_exists("free_bike_status"))
        self.assertEqual(raw_feed.feed_name, "free_bike_status")
        self.assertEqual(raw_feed.source_type, "cache")
        self.assertEqual(raw_feed.json_body, {"data": {"bikes": []}})

    def test_missing_sample_feed_records_failed_collection_status(self) -> None:
        collector = RideFeedCollector(
            mode="sample",
            feed_index_url="https://example.test/gbfs.json",
            sample_dir=self.sample_dir,
            cache_dir=self.cache_dir,
        )

        with self.assertRaises(FeedCollectionError):
            collector.get_feed_file("missing_feed")

        statuses = collector.get_collection_status()
        self.assertEqual(statuses[-1].feed_name, "missing_feed")
        self.assertFalse(statuses[-1].success)
        self.assertIn("File does not exist", statuses[-1].error_message)

    def test_live_collector_uses_gbfs_index_and_writes_cache(self) -> None:
        collector = FakeLiveRideFeedCollector(self.sample_dir, self.cache_dir)

        raw_feed = collector.get_feed_file("free_bike_status")

        self.assertEqual(raw_feed.source_type, "live")
        self.assertEqual(
            collector.requested_urls,
            [
                ("https://example.test/gbfs.json", "gbfs"),
                ("https://example.test/free_bike_status.json", "free_bike_status"),
            ],
        )
        self.assertTrue(collector.cache_exists("gbfs"))
        self.assertTrue(collector.cache_exists("free_bike_status"))

    def _write_sample_files(self) -> None:
        self._write_json("gbfs.json", sample_gbfs_index())
        self._write_json("free_bike_status.json", sample_free_bike_status())
        self._write_json("station_information.json", sample_station_information())
        self._write_json("station_status.json", sample_station_status())
        self._write_json("system_alerts.json", sample_system_alerts())

    def _write_json(self, filename: str, json_body: dict) -> None:
        (self.sample_dir / filename).write_text(json.dumps(json_body), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
