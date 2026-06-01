from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.services.ride_data_normalizer import normalize_snapshot
from backend.app.services.ride_feed_collector import RideFeedCollector
from backend.app.services.status_fallback_service import StatusFallbackService


router = APIRouter(prefix="/api", tags=["dashboard"])

_collector = RideFeedCollector()
_status_service = StatusFallbackService(_collector)


@router.get("/dashboard")
def get_dashboard_snapshot():
    status = _status_service.get_system_status()
    source = status.get("source")

    if source in {None, "none"}:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "No live, cached, or sample dashboard data is available.",
                "status": status,
            },
        )

    raw_feeds = _collector.load_dashboard_feeds(
        source=str(source),
        include_optional=True,
    )

    snapshot = normalize_snapshot(raw_feeds, source=str(source))
    snapshot["status"] = status

    return snapshot
