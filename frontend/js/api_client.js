/*
File: api_client.js

Purpose:
    Provides frontend functions for communicating with backend API
    endpoints. This module centralizes HTTP requests so the rest of
    the frontend does not need to know endpoint URLs or request
    details.

System context:
    This file is part of the PeaceHealth Rides Availability and
    Navigation Dashboard frontend. The dashboard uses these functions
    to retrieve normalized bike, hub, alert, and status information
    from the backend API.

Creation date:
    May 2026

Initial author:
    Dacian Rapolla

Modification history:
    June 2026 - Dacian Rapolla - Created dashboard API client and
    dashboard snapshot retrieval function.
*/

const API_BASE_URL = "http://localhost:8000";

export async function fetchDashboardSnapshot() {
  const response = await fetch(`${API_BASE_URL}/api/dashboard`);

  if (!response.ok) {
    throw new Error(`Dashboard request failed with status ${response.status}`);
  }

  return response.json();
}
