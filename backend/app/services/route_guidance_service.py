
"""
Title of file: route_guidance_service.py
Created: 6-1-26
Authors: Jack Sedillos
Backend service
The Route Guidance Service provides directions or route estimates from a user-selected 
starting location to a selected bike or hub. In the initial system, this may be implemented 
as an approximate walking distance and an external map link.

functions
  create_route_to_bike(start_lat, start_lon, bike) 
  create_route_to_hub(start_lat, start_lon, hub) 
  create_external_map_link(start_lat, start_lon, dest_lat, dest_lon)    
  estimate_walking_distance(start_lat, start_lon, dest_lat, dest_lon)    
"""

from __future__ import annotations

import json
import logging
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import List, Optional

from models.normalized_models import BikeLocation, HubLocation

logger = logging.getLogger(__name__)


_EARTH_RADIUS_M = 6_371_000.0
_WALK_SPEED_MS = 1.4           # ~5 km/h average pedestrian speed
_METRES_PER_FOOT = 0.3048
_METRES_PER_MILE = 1_609.344

# OSRM public demo server — swap for a self-hosted instance if needed
_OSRM_BASE_URL = "http://router.project-osrm.org"
_OSRM_PROFILE = "foot"
_OSRM_TIMEOUT_S = 5

# Google Maps walking directions base URL
_GMAPS_BASE = "https://www.google.com/maps/dir/?api=1"


@dataclass
class RouteSummary:
    """
    What the frontend needs to display a route to the user
    """

    start_latitude: float
    start_longitude: float
    destination_latitude: float
    destination_longitude: float
    destination_type: str
    destination_id: str
    distance_meters: float
    distance_text: str
    walk_minutes: float
    directions_url: str
    route_warning: Optional[str] = None
    osrm_geometry: Optional[List] = field(default=None)


class RouteGuidanceService:
    """
    Produces RouteSummary objects for a selected bike or hub destination for user
    OSRM is attempted first with a 5-second timeout, and with any failure, the service
    falls back to a straight-line Haversine estimate and gives 'route_warning' on the returned summary 
    so the frontend can give to the user
    """

    def __init__(self, use_osrm: bool = True, osrm_base_url: str = _OSRM_BASE_URL) -> None:
        self._use_osrm = use_osrm
        self._osrm_base_url = osrm_base_url.rstrip("/")


    def create_route_to_bike(self, start_lat: float, start_lon: float, bike: BikeLocation) -> RouteSummary:
        """
        Build RouteSummary from '(start_lat, start_lon)' to the bike
        """
        return self._build_summary(
            start_lat=start_lat,
            start_lon=start_lon,
            dest_lat=bike.latitude,
            dest_lon=bike.longitude,
            destination_id=bike.bike_id,
            destination_type="bike")

    def create_route_to_hub(self, start_lat: float, start_lon: float, hub: HubLocation) -> RouteSummary:
        """
        Build RouteSummary from '(start_lat, start_lon)' to the hub
        """
        return self._build_summary(
            start_lat=start_lat,
            start_lon=start_lon,
            dest_lat=hub.latitude,
            dest_lon=hub.longitude,
            destination_id=hub.station_id,
            destination_type="hub")

    def create_external_map_link(self, start_lat: float, start_lon: float, dest_lat: float, dest_lon: float) -> str:
        """
        Return Google Maps walking-directions URL
        The frontend the opens this in a new tab when the user wants specific turn-by-turn
        directions from Google instead of the in-app route that's given
        """
        params = {"origin": f"{start_lat},{start_lon}", "destination": f"{dest_lat},{dest_lon}", "travelmode": "walking"}
        return f"{_GMAPS_BASE}&{urllib.parse.urlencode(params)}"


    def estimate_walking_distance(self, start_lat: float, start_lon: float, dest_lat: float, dest_lon: float) -> float:
        """
        Returns best available walking distance estimate in metres
        OSRM first; returns straight-line Haversine if a failure occurs
        """
        if self._use_osrm:
            osrm_result = self._osrm_route(start_lat, start_lon, dest_lat, dest_lon)
            if osrm_result is not None:
                return osrm_result[0]
        return self._haversine(start_lat, start_lon, dest_lat, dest_lon)


    def _build_summary(self, start_lat: float, start_lon: float, dest_lat: float, dest_lon: float, destination_id: str, destination_type: str) -> RouteSummary:
        """Construct the RouteSummary, trying OSRM then other if not"""
        route_warning: Optional[str] = None
        osrm_geometry: Optional[List] = None

        if self._use_osrm:
            osrm_result = self._osrm_route(start_lat, start_lon, dest_lat, dest_lon)
            if osrm_result is not None:
                distance_meters, osrm_geometry = osrm_result
                logger.debug("OSRM distance %.1f m to %s %s", distance_meters, destination_type, destination_id)
            else:
                distance_meters = self._haversine(start_lat, start_lon, dest_lat, dest_lon)
                route_warning = ("Walking route unavailable — showing straight-line distance estimate.")
                logger.info("OSRM failed, using haversine for %s %s", destination_type, destination_id)
        else:
            distance_meters = self._haversine(start_lat, start_lon, dest_lat, dest_lon)
            route_warning = "Showing straight-line distance estimate."

        return RouteSummary(
            start_latitude=start_lat,
            start_longitude=start_lon,
            destination_latitude=dest_lat,
            destination_longitude=dest_lon,
            destination_type=destination_type,
            destination_id=destination_id,
            distance_meters=distance_meters,
            distance_text=self._format_distance(distance_meters),
            walk_minutes=round(distance_meters / _WALK_SPEED_MS / 60.0, 1),
            directions_url=self.create_external_map_link(start_lat, start_lon, dest_lat, dest_lon),
            route_warning=route_warning,
            osrm_geometry=osrm_geometry,
        )


    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = (math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2)
        return _EARTH_RADIUS_M * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


    def _format_distance(self, metres: float) -> str:
        """Return readable distance string scuh feet under 1000 ft, miles above"""
        feet = metres / _METRES_PER_FOOT
        if feet < 1000:
            return f"{int(round(feet))} ft"
        return f"{metres / _METRES_PER_MILE:.2f} mi"


    def _osrm_route(self, start_lat: float, start_lon: float, dest_lat: float, dest_lon: float) -> Optional[tuple[float, List]]:
        """
        Call the OSRM route API
        """
        try:
            coords = f"{start_lon},{start_lat};{dest_lon},{dest_lat}"
            url = (
                f"{self._osrm_base_url}/route/v1/{_OSRM_PROFILE}/{coords}"
                f"?overview=full&geometries=geojson&steps=false")
            req = urllib.request.Request(url, headers={"User-Agent": "PeaceHealthBikesTracker/1.0"})
            with urllib.request.urlopen(req, timeout=_OSRM_TIMEOUT_S) as resp:
                data = json.loads(resp.read().decode())

            if data.get("code") != "Ok" or not data.get("routes"):
                logger.warning("OSRM returned non-Ok code: %s", data.get("code"))
                return None

            route = data["routes"][0]
            distance_m: float = route["distance"]
            geometry: List = route["geometry"]["coordinates"]  # [[lon, lat], ...]
            return distance_m, geometry

        except Exception as exc:
            logger.warning("OSRM request failed: %s", exc)
            return None