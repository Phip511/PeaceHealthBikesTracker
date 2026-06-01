import unittest
from dataclasses import asdict

from backend.app.models.normalized_models import BikeLocation, FeedFreshness, HubLocation, SystemAlert
from backend.app.services.ride_data_normalizer import RideDataNormalizer, normalize_snapshot
from backend.tests.fixtures.gbfs_samples import (
    sample_free_bike_status,
    sample_station_information,
    sample_station_status,
    sample_system_alerts,
    sample_vehicle_status,
)


class RideDataNormalizerTests(unittest.TestCase):
    def test_normalize_bikes_returns_diagram_bike_location_fields(self) -> None:
        bikes = RideDataNormalizer().normalize_bikes(sample_free_bike_status())

        self.assertEqual(len(bikes), 1)
        self.assertIsInstance(bikes[0], BikeLocation)
        self.assertEqual(
            set(asdict(bikes[0])),
            {"bike_id", "latitude", "longitude", "is_available", "last_reported"},
        )
        self.assertEqual(bikes[0].bike_id, "bike-1")
        self.assertTrue(bikes[0].is_available)
        self.assertEqual(bikes[0].last_reported, 1780056000)

    def test_normalize_bikes_accepts_vehicle_status_feed(self) -> None:
        bikes = RideDataNormalizer().normalize_bikes(sample_vehicle_status())

        self.assertEqual(bikes[0].bike_id, "vehicle-1")
        self.assertEqual(bikes[0].latitude, 44.046)
        self.assertEqual(bikes[0].longitude, -123.073)

    def test_invalid_bike_coordinates_are_skipped_with_warning(self) -> None:
        normalizer = RideDataNormalizer()
        raw_feed = {
            "data": {
                "bikes": [
                    {"bike_id": "bad-bike", "lat": 144.0, "lon": -123.0},
                    {"bike_id": "good-bike", "lat": 44.0, "lon": -123.0},
                ]
            }
        }

        bikes = normalizer.normalize_bikes(raw_feed)

        self.assertEqual([bike.bike_id for bike in bikes], ["good-bike"])
        self.assertEqual(normalizer.warnings[-1].feed_name, "free_bike_status")
        self.assertEqual(normalizer.warnings[-1].record_id, "bad-bike")

    def test_normalize_hubs_joins_station_information_and_status(self) -> None:
        hubs = RideDataNormalizer().normalize_hubs(sample_station_information(), sample_station_status())

        self.assertEqual(len(hubs), 1)
        self.assertIsInstance(hubs[0], HubLocation)
        self.assertEqual(
            set(asdict(hubs[0])),
            {
                "station_id",
                "name",
                "latitude",
                "longitude",
                "available_bikes",
                "capacity",
                "last_reported",
            },
        )
        self.assertEqual(hubs[0].station_id, "hub-1")
        self.assertEqual(hubs[0].available_bikes, 3)
        self.assertEqual(hubs[0].last_reported, 1780056000)

    def test_normalize_hubs_accepts_num_vehicles_available(self) -> None:
        station_status = {
            "data": {
                "stations": [
                    {
                        "station_id": "hub-1",
                        "num_vehicles_available": 4,
                    }
                ]
            }
        }

        hubs = RideDataNormalizer().normalize_hubs(sample_station_information(), station_status)

        self.assertEqual(hubs[0].available_bikes, 4)

    def test_normalize_alerts_returns_diagram_system_alert_fields(self) -> None:
        raw_feed = sample_system_alerts()
        raw_feed["data"]["alerts"][0] = {
            "alert_id": "alert-1",
            "summary": [{"text": "Station closed", "language": "en"}],
            "description": {"translation": [{"text": "Construction nearby"}]},
            "informed_entities": [{"station_id": "hub-1"}],
            "times": [{"start": 1780056000, "end": 1780060000}],
        }

        alerts = RideDataNormalizer().normalize_alerts(raw_feed)

        self.assertEqual(len(alerts), 1)
        self.assertIsInstance(alerts[0], SystemAlert)
        self.assertEqual(
            set(asdict(alerts[0])),
            {
                "alert_id",
                "summary",
                "description",
                "affected_station_ids",
                "start_time",
                "end_time",
            },
        )
        self.assertEqual(alerts[0].summary, "Station closed")
        self.assertEqual(alerts[0].description, "Construction nearby")
        self.assertEqual(alerts[0].affected_station_ids, ["hub-1"])

    def test_normalize_timestamp_returns_feed_freshness_flags(self) -> None:
        freshness = RideDataNormalizer(source="sample").normalize_timestamp(
            {
                "last_updated": "2026-05-29T12:00:00Z",
                "ttl": 30,
                "version": "2.3",
            }
        )

        self.assertIsInstance(freshness, FeedFreshness)
        self.assertEqual(
            set(asdict(freshness)),
            {"source", "last_updated", "is_live", "is_cached", "is_sample"},
        )
        self.assertEqual(freshness.source, "sample")
        self.assertEqual(freshness.last_updated, 1780056000)
        self.assertFalse(freshness.is_live)
        self.assertFalse(freshness.is_cached)
        self.assertTrue(freshness.is_sample)

    def test_normalize_snapshot_returns_api_ready_dicts(self) -> None:
        snapshot = normalize_snapshot(
            {
                "free_bike_status": sample_free_bike_status(),
                "station_information": sample_station_information(),
                "station_status": sample_station_status(),
                "system_alerts": sample_system_alerts(),
            },
            source="live",
        )

        self.assertEqual(snapshot["bikes"][0]["bike_id"], "bike-1")
        self.assertEqual(snapshot["hubs"][0]["station_id"], "hub-1")
        self.assertEqual(snapshot["hubs"][0]["available_bikes"], 3)
        self.assertTrue(snapshot["freshness"]["is_live"])


if __name__ == "__main__":
    unittest.main()
