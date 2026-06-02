"""
Title of file: availability_query_service.py
Created: 6-1-26
Authors: Jack Sedillos
Backend service

The Availability Query Service answers project-specific questions about available bikes and hubs. 
It filters unavailable entries, computes distances, ranks nearby destinations, and provides simplified 
results to the Dashboard API.It answers questions such as:
• “Which bikes are currently visible?”
• “Which hubs have bikes available?”
• “Which bikes or hubs are nearest to this coordinate?”

functions
  list_available_bikes(bikes):  List[BikeLocation]
  list_available_hubs(hubs):   List[HubLocation]
  find_nearest_bikes(bikes, latitude, longitude, limit):  List[NearbyResult]
  find_nearest_hubs(hubs, latitude, longitude, limit):   list[NearbyResult]
  distance_between(lat1, lon1, lat2, lon2): float
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import List, Optional

from models.normalized_models import BikeLocation, HubLocation

logger = logging.getLogger(__name__)

_DEFAULT_LIMIT = 10
_EARTH_RADIUS_M = 6_371_000.0


@dataclass
class NearbyResult:
    """Gets result thats ranked from find_nearest_bikes and find_nearest_hubs"""

    destination_id: str    # bike_id or station_id
    destination_type: str  # "bike" or "hub"
    distance_meters: float
    rank: int              # 1 is closest



class AvailabilityQueryService:
    """
    service for bike/hub availability queries
    one instance can be reused on all requests
    """

    def distance_between(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Return the distance in metres between two points
        """
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = (math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2)
        return _EARTH_RADIUS_M * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


    def list_available_bikes(self, bikes: List[BikeLocation]) -> List[BikeLocation]:
        """
        Return only bikes whose ``is_available`` is True in call
        """
        available = [b for b in bikes if b.is_available]
        logger.debug("list_available_bikes: %d / %d available", len(available), len(bikes))
        return available


    def list_available_hubs(self, hubs: List[HubLocation]) -> List[HubLocation]:
        """
        Return hubs with either at least one available bike, or unknown availability (None)
        Hubs with a reporting  of 0 available bikes are excluded so the user
        is not directed to an empty station with no bikes
        """
        available = [
            h for h in hubs
            if h.available_bikes is None or h.available_bikes > 0]
        logger.debug("list_available_hubs: %d / %d usable", len(available), len(hubs))
        return available


    def find_nearest_bikes(self, bikes: List[BikeLocation], latitude: float, longitude: float, limit: Optional[int] = None) -> List[NearbyResult]:
        """
        Return the closest available bikes ranked by distance
        bikes are in 'list_available_bikes' are considered
        """
        limit = limit or _DEFAULT_LIMIT
        available = self.list_available_bikes(bikes)

        if not available:
            logger.info("find_nearest_bikes: no available bikes in dataset")
            return []

        scored = sorted(
            (
                (self.distance_between(latitude, longitude, b.latitude, b.longitude), b)
                for b in available
            ),
            key=lambda t: t[0],
        )

        results = [
            NearbyResult(destination_id=b.bike_id, destination_type="bike", distance_meters=dist, rank=rank,)
            for rank, (dist, b) in enumerate(scored[:limit], start=1)
        ]

        logger.debug("find_nearest_bikes: %d results from (%.5f, %.5f)", len(results), latitude, longitude)
        return results


    def find_nearest_hubs(self, hubs: List[HubLocation], latitude: float, longitude: float, limit: Optional[int] = None) -> List[NearbyResult]:
        """
        Return the closest usable hubs ranked by distance
        check 'list_available_hubs' for considered hubs
        """
        limit = limit or _DEFAULT_LIMIT
        available = self.list_available_hubs(hubs)

        if not available:
            logger.info("find_nearest_hubs: no hubs with available bikes")
            return []

        scored = sorted(
            (
                (self.distance_between(latitude, longitude, h.latitude, h.longitude), h)
                for h in available
            ),
            key=lambda t: t[0],
        )

        results = [
            NearbyResult(destination_id=h.station_id, destination_type="hub", distance_meters=dist, rank=rank)
            for rank, (dist, h) in enumerate(scored[:limit], start=1)
        ]

        logger.debug(
            "find_nearest_hubs: %d results from (%.5f, %.5f)",
            len(results), latitude, longitude,
        )
        return results


    def find_nearest_any(self, bikes: List[BikeLocation], hubs: List[HubLocation], latitude: float, longitude: float, limit: Optional[int] = None) -> List[NearbyResult]:
        """
        Return closest bikes + hubs merged and ranked as one, together
        "show me anything nearby" dashboard view where the user has not filtered to bikes-only or hubs-only
        """
        limit = limit or _DEFAULT_LIMIT
        combined = sorted(
            self.find_nearest_bikes(bikes, latitude, longitude, limit)
            + self.find_nearest_hubs(hubs, latitude, longitude, limit),
            key=lambda r: r.distance_meters,
        )
        # Re-rank them after merging the two sorted lists
        for i, result in enumerate(combined[:limit], start=1):
            result.rank = i
        return combined[:limit]