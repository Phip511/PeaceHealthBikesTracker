"""
File: test_status_fallback_service.py

Purpose:
    Provides unit tests for the StatusFallbackService. These tests verify
    that the service correctly selects between live, cached, and sample
    data sources and returns the expected status information for the
    frontend and API clients.

System context:
    This file is part of the PeaceHealth Rides Availability and Navigation
    Dashboard backend test suite. The tests focus only on fallback and
    status-selection behavior, so they use a fake collector instead of
    making live network requests or reading real sample/cache files.

Creation date:
    May 2026

Initial author:
    Dacian Rapolla

Modification history:
    June 2026 - Dacian Rapolla - Added unit tests for StatusFallbackService
    live/cache/sample fallback behavior.
"""

# unittest is Python's standard testing framework. It is used here so the
# tests can run without adding another testing dependency.
import unittest

# FeedCollectionError is raised by the fake collector when a source should
# be treated as unavailable.
from backend.app.models.feed_models import FeedCollectionError

# StatusFallbackService is the unit under test.
from backend.app.services.status_fallback_service import StatusFallbackService


# ---------------------------------------------------------------------------
# Fake Collector
# ---------------------------------------------------------------------------
# The real RideFeedCollector performs file and network operations. These tests
# replace it with FakeCollector so each test can control exactly which data
# sources are available.
# ---------------------------------------------------------------------------
class FakeCollector:

    # Store the set of source names that should succeed during a test.
    def __init__(self, available_sources):
        self.available_sources = available_sources

    # Simulate the RideFeedCollector.load_dashboard_feeds method.
    # If the requested source is unavailable, raise the same error type
    # that the real collector would raise.
    def load_dashboard_feeds(self, source="live", include_optional=True):
        if source not in self.available_sources:
            raise FeedCollectionError("dashboard", source, "Source unavailable.")

        # Required dashboard feeds use fixed timestamps so tests can verify
        # feed status and latest-update calculations deterministically.
        feeds = {
            "free_bike_status": {"last_updated": 100},
            "station_information": {"last_updated": 200},
            "station_status": {"last_updated": 300},
        }

        # Optional alerts feed is included only when requested, matching the
        # behavior expected from the real collector.
        if include_optional:
            feeds["system_alerts"] = {"last_updated": 400}

        return feeds


# ---------------------------------------------------------------------------
# StatusFallbackService Tests
# ---------------------------------------------------------------------------
# These tests verify the source-selection priority:
#
#   live -> cache -> sample -> error
#
# They also verify that the returned status dictionary contains feed-level
# information needed by the frontend.
# ---------------------------------------------------------------------------
class StatusFallbackServiceTests(unittest.TestCase):

    # Verify that live data is preferred whenever live data is available.
    def test_uses_live_when_live_is_available(self):
        service = StatusFallbackService(FakeCollector({"live", "sample"}))

        status = service.get_system_status()

        self.assertEqual(status["status"], "ok")
        self.assertEqual(status["source"], "live")
        self.assertTrue(status["using_live_data"])
        self.assertFalse(status["using_sample_data"])
        self.assertEqual(status["source_label"], "Live Data")

    # Verify that cache data is selected when live data fails but cache
    # data is available.
    def test_falls_back_to_cache_when_live_fails(self):
        service = StatusFallbackService(FakeCollector({"cache", "sample"}))

        status = service.get_system_status()

        self.assertEqual(status["status"], "degraded")
        self.assertEqual(status["source"], "cache")
        self.assertTrue(status["using_cached_data"])
        self.assertFalse(status["using_live_data"])
        self.assertIn("Live data is unavailable", status["warnings"][0])

    # Verify that sample data is selected when neither live nor cached
    # data can be used.
    def test_falls_back_to_sample_when_live_and_cache_fail(self):
        service = StatusFallbackService(FakeCollector({"sample"}))

        status = service.get_system_status()

        self.assertEqual(status["status"], "degraded")
        self.assertEqual(status["source"], "sample")
        self.assertTrue(status["using_sample_data"])
        self.assertEqual(status["source_label"], "Sample Data")

    # Verify that an error status is returned when no source can provide
    # dashboard data.
    def test_returns_error_when_no_sources_available(self):
        service = StatusFallbackService(FakeCollector(set()))

        status = service.get_system_status()

        self.assertEqual(status["status"], "error")
        self.assertEqual(status["source"], "none")
        self.assertEqual(
            status["visible_message"],
            "No live, cached, or sample bike-share data is available.",
        )

    # Verify that feed-level status objects are included in the system
    # status response and that the most recent timestamp is reported.
    def test_reports_feed_statuses(self):
        service = StatusFallbackService(FakeCollector({"live"}))

        status = service.get_system_status()

        feed_names = [feed["feed_name"] for feed in status["feeds"]]

        self.assertIn("free_bike_status", feed_names)
        self.assertIn("station_information", feed_names)
        self.assertIn("station_status", feed_names)
        self.assertIn("system_alerts", feed_names)
        self.assertEqual(status["last_successful_update"], 400)


# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------
# Allows this test file to be executed directly with:
#
#   python backend/tests/test_status_fallback_service.py
#
# The tests can also be run through unittest discovery.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    unittest.main()
