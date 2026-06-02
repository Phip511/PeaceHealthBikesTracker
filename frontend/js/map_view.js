/*
File: map_view.js

Purpose:
    Creates and configures the Leaflet map used by the Bike Finder Map
    feature. This module centralizes map initialization so the rest of
    the frontend can work with a fully configured map object.

System context:
    This file is part of the PeaceHealth Rides Availability and
    Navigation Dashboard frontend. It initializes the OpenStreetMap
    base layer and sets the default view used when the dashboard
    first loads.

Creation date:
    May 2026

Initial author:
    Dacian Rapolla

Modification history:
    June 2026 - Dacian Rapolla - Created Leaflet map initialization
    module and configured OpenStreetMap tile layer support.
*/

const EUGENE_CENTER = [44.0521, -123.0868];
const DEFAULT_ZOOM = 13;

export function createMap(elementId) {
  const map = L.map(elementId).setView(EUGENE_CENTER, DEFAULT_ZOOM);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  return map;
}
