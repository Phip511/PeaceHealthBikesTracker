"""
File: main.py

Purpose:
    Creates and configures the FastAPI application used by the
    PeaceHealth Rides Availability and Navigation Dashboard backend.

System context:
    This file serves as the backend entry point. It initializes the
    FastAPI application, configures middleware, registers API routes,
    and provides a simple root endpoint used for service verification.

Creation date:
    May 2026

Initial author:
    Dacian Rapolla

Modification history:
    June 2026 - Dacian Rapolla - Created backend application entry point,
    registered API routes, and configured CORS support.
"""

from __future__ import annotations

# FastAPI provides the web framework used by the backend.
from fastapi import FastAPI

# CORSMiddleware allows frontend applications running on different
# origins to communicate with the backend API.
from fastapi.middleware.cors import CORSMiddleware

# Dashboard router provides dashboard snapshot endpoints.
from backend.app.api.routes_dashboard import router as dashboard_router

# Status router provides system health and fallback status endpoints.
from backend.app.api.routes_status import router as status_router


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------
# Create the primary backend application instance. This object manages
# route registration, middleware configuration, and API documentation.
# ---------------------------------------------------------------------------
app = FastAPI(
    title="PeaceHealth Rides Availability and Navigation Dashboard API",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Cross-Origin Resource Sharing (CORS)
# ---------------------------------------------------------------------------
# Allow browser-based frontend clients to communicate with the backend.
# During development, all origins are permitted to simplify testing.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,

    # Allow requests from any origin.
    allow_origins=["*"],

    # Credentials are not required for this application.
    allow_credentials=False,

    # Permit all standard HTTP methods.
    allow_methods=["*"],

    # Permit all request headers.
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Route Registration
# ---------------------------------------------------------------------------
# Register API route groups with the FastAPI application.
#
# /api/status
#     Provides system health and fallback status information.
#
# /api/dashboard
#     Provides normalized dashboard data used by the frontend.
# ---------------------------------------------------------------------------
app.include_router(status_router)
app.include_router(dashboard_router)


# ---------------------------------------------------------------------------
# GET /
#
# Purpose:
#     Simple root endpoint used to verify that the backend service is
#     running successfully.
#
# Returns:
#     A small status message and the location of the primary status
#     endpoint.
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "message": "PeaceHealth Rides backend is running.",
        "status_endpoint": "/api/status",
    }
