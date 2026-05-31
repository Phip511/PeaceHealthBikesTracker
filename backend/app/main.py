from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes_dashboard import router as dashboard_router
from backend.app.api.routes_status import router as status_router

app = FastAPI(
    title="PeaceHealth Rides Availability and Navigation Dashboard API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(status_router)
app.include_router(dashboard_router)

@app.get("/")
def root():
    return {
        "message": "PeaceHealth Rides backend is running.",
        "status_endpoint": "/api/status",
    }
