"""
File: routes_dashboard.py

Purpose:
    Defines the dashboard snapshot API endpoint used by the frontend.
    This endpoint combines normalized bike-share data with system
    status information and returns a complete dashboard data snapshot
    in a single response.

System context:
    This file is part of the PeaceHealth Rides Availability and Navigation
    Dashboard backend. The frontend calls this endpoint when loading the
    map view. The endpoint coordinates status evaluation, feed loading,
    data normalization, and snapshot assembly.

Creation date:
    May 2026

Initial author:
    Dacian Rapolla

Modification history:
    June 2026 - Dacian Rapolla - Created dashboard snapshot endpoint and
    integrated status, feed collection, and normalization services.
"""

from __future__ import annotations

# APIRouter groups dashboard-related endpoints.
# HTTPException allows the API to return appropriate error responses.
from fastapi import APIRouter, HTTPException

# normalize_snapshot converts raw GBFS feed data into a simplified
# frontend-friendly representation.
from backend.app.services.ride_data_normalizer import normalize_snapshot

# RideFeedCollector retrieves live, cached, or sample feed data.
from backend.app.services.ride_feed_collector import RideFeedCollector

# StatusFallbackService determines which data source should be used
# and generates frontend-facing status information.
from backend.app.services.status_fallback_service import StatusFallbackService


# ---------------------------------------------------------------------------
# Router Configuration
# ---------------------------------------------------------------------------
# All dashboard-related endpoints are grouped under the /api prefix and
# tagged as "dashboard" for API documentation purposes.
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/api", tags=["dashboard"])


# ---------------------------------------------------------------------------
# Service Instances
# ---------------------------------------------------------------------------
# Create shared service instances used by incoming requests.
#
# The StatusFallbackService reuses the same RideFeedCollector instance so
# status checks and feed loading operate against a consistent collector.
# ---------------------------------------------------------------------------
_collector = RideFeedCollector()
_status_service = StatusFallbackService(_collector)


# ---------------------------------------------------------------------------
# GET /api/dashboard
#
# Returns:
#     A complete dashboard snapshot containing:
#       - normalized bike data
#       - normalized hub/station data
#       - system alerts
#       - freshness information
#       - current status and fallback information
#
# Flow:
#     1. Determine the current system status.
#     2. Determine which source should be used.
#     3. Load feeds from that source.
#     4. Normalize the raw feed data.
#     5. Attach status information.
#     6. Return the completed snapshot.
# ---------------------------------------------------------------------------
@router.get("/dashboard")
def get_dashboard_snapshot():

    # Determine the current source being used by the dashboard and gather
    # status information for frontend displays.
    status = _status_service.get_system_status()
    source = status.get("source")

    # If no valid source exists, return a service unavailable response
    # rather than attempting to build a dashboard snapshot.
    if source in {None, "none"}:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "No live, cached, or sample dashboard data is available.",
                "status": status,
            },
        )

    # Load feeds from the source selected by the StatusFallbackService.
    raw_feeds = _collector.load_dashboard_feeds(
        source=str(source),
        include_optional=True,
    )

    # Convert raw feed data into a simplified frontend-friendly snapshot.
    snapshot = normalize_snapshot(
        raw_feeds,
        source=str(source),
    )

    # Attach status information so the frontend can display freshness,
    # fallback warnings, and source information without making an
    # additional request.
    snapshot["status"] = status

    # Return the completed dashboard snapshot.
    return snapshot
