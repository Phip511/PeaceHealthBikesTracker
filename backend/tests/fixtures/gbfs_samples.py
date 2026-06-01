"""Reusable GBFS-shaped sample payloads for unit tests."""

from __future__ import annotations

from typing import Any, Dict


def sample_gbfs_index() -> Dict[str, Any]:
    return {
        "data": {
            "en": {
                "feeds": [
                    {"name": "free_bike_status", "url": "free_bike_status.json"},
                    {"name": "station_information", "url": "station_information.json"},
                    {"name": "station_status", "url": "station_status.json"},
                    {"name": "system_alerts", "url": "system_alerts.json"},
                ]
            }
        }
    }


def sample_free_bike_status() -> Dict[str, Any]:
    return {
        "last_updated": 1780056000,
        "ttl": 30,
        "version": "2.3",
        "data": {
            "bikes": [
                {
                    "bike_id": "bike-1",
                    "lat": 44.045,
                    "lon": -123.072,
                    "is_reserved": 0,
                    "is_disabled": 0,
                }
            ]
        },
    }


def sample_vehicle_status() -> Dict[str, Any]:
    return {
        "data": {
            "en": {
                "vehicles": [
                    {
                        "vehicle_id": "vehicle-1",
                        "lat": 44.046,
                        "lon": -123.073,
                        "is_reserved": False,
                        "is_disabled": False,
                    }
                ]
            }
        }
    }


def sample_station_information() -> Dict[str, Any]:
    return {
        "data": {
            "stations": [
                {
                    "station_id": "hub-1",
                    "name": "UO Station",
                    "lat": 44.044,
                    "lon": -123.071,
                    "capacity": 8,
                }
            ]
        }
    }


def sample_station_status() -> Dict[str, Any]:
    return {
        "last_updated": 1780056000,
        "data": {
            "stations": [
                {
                    "station_id": "hub-1",
                    "num_bikes_available": 3,
                    "is_installed": 1,
                    "is_renting": 1,
                    "is_returning": 1,
                }
            ]
        },
    }


def sample_system_alerts() -> Dict[str, Any]:
    return {
        "data": {
            "alerts": [
                {
                    "alert_id": "alert-1",
                    "summary": "Test alert",
                    "description": "Details",
                    "station_ids": ["hub-1"],
                }
            ]
        }
    }
