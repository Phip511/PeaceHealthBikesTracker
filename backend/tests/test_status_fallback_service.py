import unittest

from backend.app.models.feed_models import FeedCollectionError
from backend.app.services.status_fallback_service import StatusFallbackService


class FakeCollector:
    def __init__(self, available_sources):
        self.available_sources = available_sources

    def load_dashboard_feeds(self, source="live", include_optional=True):
        if source not in self.available_sources:
            raise FeedCollectionError("dashboard", source, "Source unavailable.")

        feeds = {
            "free_bike_status": {"last_updated": 100},
            "station_information": {"last_updated": 200},
            "station_status": {"last_updated": 300},
        }

        if include_optional:
            feeds["system_alerts"] = {"last_updated": 400}

        return feeds


class StatusFallbackServiceTests(unittest.TestCase):
    def test_uses_live_when_live_is_available(self):
        service = StatusFallbackService(FakeCollector({"live", "sample"}))

        status = service.get_system_status()

        self.assertEqual(status["status"], "ok")
        self.assertEqual(status["source"], "live")
        self.assertTrue(status["using_live_data"])
        self.assertFalse(status["using_sample_data"])
        self.assertEqual(status["source_label"], "Live Data")

    def test_falls_back_to_cache_when_live_fails(self):
        service = StatusFallbackService(FakeCollector({"cache", "sample"}))

        status = service.get_system_status()

        self.assertEqual(status["status"], "degraded")
        self.assertEqual(status["source"], "cache")
        self.assertTrue(status["using_cached_data"])
        self.assertFalse(status["using_live_data"])
        self.assertIn("Live data is unavailable", status["warnings"][0])

    def test_falls_back_to_sample_when_live_and_cache_fail(self):
        service = StatusFallbackService(FakeCollector({"sample"}))

        status = service.get_system_status()

        self.assertEqual(status["status"], "degraded")
        self.assertEqual(status["source"], "sample")
        self.assertTrue(status["using_sample_data"])
        self.assertEqual(status["source_label"], "Sample Data")

    def test_returns_error_when_no_sources_available(self):
        service = StatusFallbackService(FakeCollector(set()))

        status = service.get_system_status()

        self.assertEqual(status["status"], "error")
        self.assertEqual(status["source"], "none")
        self.assertEqual(status["visible_message"], "No live, cached, or sample bike-share data is available.")

    def test_reports_feed_statuses(self):
        service = StatusFallbackService(FakeCollector({"live"}))

        status = service.get_system_status()

        feed_names = [feed["feed_name"] for feed in status["feeds"]]

        self.assertIn("free_bike_status", feed_names)
        self.assertIn("station_information", feed_names)
        self.assertIn("station_status", feed_names)
        self.assertIn("system_alerts", feed_names)
        self.assertEqual(status["last_successful_update"], 400)


if __name__ == "__main__":
    unittest.main()
