from __future__ import annotations

from fastapi import APIRouter

from backend.app.services.status_fallback_service import StatusFallbackService


router = APIRouter(prefix="/api", tags=["status"])

_status_service = StatusFallbackService()


@router.get("/status")
def get_status():
    return _status_service.get_system_status()
