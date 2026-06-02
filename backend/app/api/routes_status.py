"""
File: routes_status.py

Purpose:
    Defines the API endpoint used to retrieve system status information.
    This endpoint provides frontend clients with information about
    current data sources, feed availability, fallback status, and
    system health.

System context:
    This file is part of the PeaceHealth Rides Availability and Navigation
    Dashboard backend. The endpoint defined here serves as the primary
    interface between the frontend status displays and the Status
    Fallback Service.

Creation date:
    May 2026

Initial author:
    Dacian Rapolla

Modification history:
    June 2026 - Dacian Rapolla - Created status endpoint and integrated
    StatusFallbackService.
"""

from __future__ import annotations

# APIRouter allows related API endpoints to be grouped together and
# registered with the FastAPI application.
from fastapi import APIRouter

# StatusFallbackService performs all status evaluation and fallback
# source selection logic.
from backend.app.services.status_fallback_service import StatusFallbackService


# ---------------------------------------------------------------------------
# Router Configuration
# ---------------------------------------------------------------------------
# All endpoints in this file are registered under the /api prefix and
# grouped under the "status" tag for API documentation purposes.
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/api", tags=["status"])


# ---------------------------------------------------------------------------
# Service Instance
# ---------------------------------------------------------------------------
# Create a single StatusFallbackService instance that will be reused
# for incoming requests.
# ---------------------------------------------------------------------------
_status_service = StatusFallbackService()


# ---------------------------------------------------------------------------
# GET /api/status
#
# Returns:
#     A JSON representation of the current dashboard status, including:
#       - active data source
#       - live/cache/sample availability
#       - feed-level status information
#       - freshness timestamps
#       - warning messages
#
# The frontend uses this endpoint to display status indicators,
# degraded-mode warnings, and data freshness information.
# ---------------------------------------------------------------------------
@router.get("/status")
def get_status():
    return _status_service.get_system_status()
