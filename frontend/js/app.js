/*
File: app.js

Purpose:
    Serves as the primary frontend controller for the PeaceHealth Rides
    Availability and Navigation Dashboard. This module coordinates map
    initialization, dashboard data loading, marker rendering, routing,
    alerts, status displays, destination details, nearby location
    recommendations, and user interface updates.

System context:
    This file acts as the integration layer between frontend modules.
    It retrieves dashboard data from the backend API, initializes the
    map, renders bikes and hubs, displays status and freshness
    information, manages route generation, processes system alerts,
    and updates user-facing dashboard panels.

Creation date:
    May 2026

Initial author:
    Dacian Rapolla

Modification history:
    June 2026 - Dacian Rapolla - Created frontend application controller.
    June 2026 - Dacian Rapolla - Added dashboard snapshot loading and
    status display integration.
    June 2026 - Dacian Rapolla - Added destination details and marker
    selection handling.
    June 2026 - Dacian Rapolla - Added route generation and browser
    location support.
    June 2026 - Dacian Rapolla - Added system alert rendering and
    degraded-mode messaging.
    June 2026 - Dacian Rapolla - Added nearby bike and hub list view.
*/

import { fetchDashboardSnapshot } from "./api_client.js";
import { createMap } from "./map_view.js";
import { renderBikeMarkers, renderHubMarkers } from "./marker_renderer.js";
import {
  clearRoute,
  displayRouteToDestination,
  enableRouteDisplay,
  useBrowserLocation,
} from "./route_display.js";
import { renderAlerts } from "./alert_renderer.js";

const map = createMap("map");

const dataStatusElement = document.querySelector("#data-status");
const bikeCountElement = document.querySelector("#bike-count");
const hubCountElement = document.querySelector("#hub-count");
const destinationDetailsElement = document.querySelector("#destination-details");
const freshnessDetailsElement = document.querySelector("#freshness-details");
const routeDetailsElement = document.querySelector("#route-details");
const useLocationButton = document.querySelector("#use-location-button");
const clearRouteButton = document.querySelector("#clear-route-button");
const alertsPanelElement = document.querySelector("#alerts-panel");
const modeWarningElement = document.querySelector("#mode-warning");
const nearbyListElement = document.querySelector("#nearby-list");

let latestSnapshot = null;

enableRouteDisplay(map, routeDetailsElement, updateNearbyList);

useLocationButton.addEventListener("click", () => {
    useBrowserLocation(map, routeDetailsElement, updateNearbyList);
  });

clearRouteButton.addEventListener("click", () => {
  clearRoute(map, routeDetailsElement);
});

loadDashboard();

async function loadDashboard() {
  try {
    const snapshot = await fetchDashboardSnapshot();
    
    latestSnapshot = snapshot;

    renderBikeMarkers(map, snapshot.bikes || [], showDestinationDetails);
    renderHubMarkers(map, snapshot.hubs || [], showDestinationDetails);
    renderAlerts(
       map,
       snapshot.alerts || [],
       alertsPanelElement,
    ); 

    updateCounts(snapshot);
    updateStatus(snapshot.status);
    updateFreshness(snapshot);
    updateModeWarning(snapshot.status);
  } catch (error) {
    console.error(error);
    dataStatusElement.textContent = "Could not load dashboard data.";
    dataStatusElement.className = "status-pill error";

    freshnessDetailsElement.innerHTML = `
      <p><span class="details-label">Status:</span> <span class="source-error">Error</span></p>
      <p>Could not load freshness information.</p>
    `;
    updateModeWarning({
  source: "error",
  status: "error",
  visible_message: "Dashboard data could not be loaded. Check that the backend is running.",
});
  }
}

function updateCounts(snapshot) {
  const bikeCount = Array.isArray(snapshot.bikes) ? snapshot.bikes.length : 0;
  const hubCount = Array.isArray(snapshot.hubs) ? snapshot.hubs.length : 0;

  bikeCountElement.textContent = `Bikes: ${bikeCount}`;
  hubCountElement.textContent = `Hubs: ${hubCount}`;
}

function updateStatus(status) {
  if (!status) {
    dataStatusElement.textContent = "Unknown data status.";
    dataStatusElement.className = "status-pill error";
    return;
  }

  dataStatusElement.textContent = status.visible_message || status.source_label;
  dataStatusElement.className = `status-pill ${status.source}`;
}

function updateFreshness(snapshot) {
  const freshness = snapshot.freshness || {};
  const status = snapshot.status || {};
  const source = status.source || freshness.source || "unknown";
  const sourceLabel = status.source_label || source;
  const freshnessTime = freshness.last_updated || status.last_successful_update;
  const warnings = collectWarnings(snapshot);

  freshnessDetailsElement.innerHTML = `
    <p><span class="details-label">Source:</span> <span class="${sourceClass(source)}">${escapeHtml(sourceLabel)}</span></p>
    <p><span class="details-label">Last updated:</span> ${formatTimestamp(freshnessTime)}</p>
    <p><span class="details-label">Live feed available:</span> ${formatYesNo(status.live_feed_available)}</p>
    <p><span class="details-label">Cached data available:</span> ${formatYesNo(status.cache_data_available)}</p>
    <p><span class="details-label">Sample data available:</span> ${formatYesNo(status.sample_data_available)}</p>
    ${renderWarnings(warnings)}
  `;
}

function showDestinationDetails(destination) {
  const typeLabel = destination.type === "bike" ? "Bike" : "Hub";
  const availableBikesText =
    destination.availableBikes === null || destination.availableBikes === undefined
      ? "N/A"
      : destination.availableBikes;

  destinationDetailsElement.innerHTML = `
    <p><span class="details-label">Type:</span> ${typeLabel}</p>
    <p><span class="details-label">Name:</span> ${escapeHtml(destination.name)}</p>
    <p><span class="details-label">ID:</span> ${escapeHtml(destination.id)}</p>
    <p><span class="details-label">Latitude:</span> ${destination.latitude.toFixed(6)}</p>
    <p><span class="details-label">Longitude:</span> ${destination.longitude.toFixed(6)}</p>
    <p><span class="details-label">Available bikes:</span> ${availableBikesText}</p>
    <p><span class="details-label">Last reported:</span> ${formatTimestamp(destination.lastReported)}</p>
  `;
  displayRouteToDestination(map, routeDetailsElement, destination);
}

function collectWarnings(snapshot) {
  const warnings = [];

  if (Array.isArray(snapshot.warnings)) {
    snapshot.warnings.forEach((warning) => {
      if (typeof warning === "string") {
        warnings.push(warning);
      } else if (warning && warning.message) {
        warnings.push(warning.message);
      }
    });
  }

  if (snapshot.status && Array.isArray(snapshot.status.warnings)) {
    snapshot.status.warnings.forEach((warning) => warnings.push(warning));
  }

  return warnings;
}

function renderWarnings(warnings) {
  if (!warnings.length) {
    return `<p><span class="details-label">Warnings:</span> None</p>`;
  }

  const warningItems = warnings
    .map((warning) => `<li>${escapeHtml(warning)}</li>`)
    .join("");

  return `
    <p><span class="details-label">Warnings:</span></p>
    <ul class="warning-list">${warningItems}</ul>
  `;
}

function sourceClass(source) {
  if (source === "live") {
    return "source-live";
  }

  if (source === "cache") {
    return "source-cache";
  }

  if (source === "sample") {
    return "source-sample";
  }

  return "source-error";
}

function formatYesNo(value) {
  if (value === true) {
    return "Yes";
  }

  if (value === false) {
    return "No";
  }

  return "Unknown";
}

function formatTimestamp(epochSeconds) {
  if (!epochSeconds) {
    return "Unknown";
  }

  return new Date(epochSeconds * 1000).toLocaleString();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function updateModeWarning(status) {
  if (!status) {
    modeWarningElement.textContent =
      "Data mode is unknown. Availability information may be incomplete.";
    modeWarningElement.className = "mode-warning error";
    return;
  }

  const source = status.source || "unknown";
  const statusValue = status.status || "unknown";

  if (source === "live" && statusValue === "ok") {
    modeWarningElement.textContent =
      "Live availability data is active.";
    modeWarningElement.className = "mode-warning live hidden";
    return;
  }

  if (source === "cache") {
    modeWarningElement.textContent =
      "Live data could not be refreshed. Cached availability data is being displayed and may be stale.";
    modeWarningElement.className = "mode-warning cache";
    return;
  }

  if (source === "sample") {
    modeWarningElement.textContent =
      "Sample data is being displayed for demonstration. It does not represent current bike availability.";
    modeWarningElement.className = "mode-warning sample";
    return;
  }

  if (statusValue === "degraded") {
    modeWarningElement.textContent =
      status.visible_message ||
      "The system is running in degraded mode. Availability data may be incomplete or stale.";
    modeWarningElement.className = "mode-warning degraded";
    return;
  }

  modeWarningElement.textContent =
    status.visible_message ||
    "Dashboard data could not be loaded. Availability information may be unavailable.";
  modeWarningElement.className = "mode-warning error";
}

function updateNearbyList() {
  const startLocation = window.currentStartLocation;

  if (!startLocation || !latestSnapshot) {
    nearbyListElement.innerHTML =
      "<p>Choose a start location to see nearby bikes and hubs.</p>";
    return;
  }

  const bikes = (latestSnapshot.bikes || [])
    .filter((bike) => bike.is_available)
    .map((bike) => ({
      type: "bike",
      id: bike.bike_id,
      name: "Available Bike",
      latitude: bike.latitude,
      longitude: bike.longitude,
      availableBikes: null,
      lastReported: bike.last_reported,
      distanceMeters: distanceBetweenMeters(startLocation, {
        latitude: bike.latitude,
        longitude: bike.longitude,
      }),
    }));

  const hubs = (latestSnapshot.hubs || [])
    .filter((hub) => hub.available_bikes === null || hub.available_bikes > 0)
    .map((hub) => ({
      type: "hub",
      id: hub.station_id,
      name: hub.name,
      latitude: hub.latitude,
      longitude: hub.longitude,
      availableBikes: hub.available_bikes,
      lastReported: hub.last_reported,
      distanceMeters: distanceBetweenMeters(startLocation, {
        latitude: hub.latitude,
        longitude: hub.longitude,
      }),
    }));

  const nearbyOptions = [...bikes, ...hubs]
    .sort((a, b) => a.distanceMeters - b.distanceMeters)
    .slice(0, 5);

  if (!nearbyOptions.length) {
    nearbyListElement.innerHTML = "<p>No nearby available bikes or hubs found.</p>";
    return;
  }

  nearbyListElement.innerHTML = nearbyOptions
    .map(
      (option, index) => `
        <button class="nearby-button" data-nearby-index="${index}">
          <div class="nearby-title">${escapeHtml(option.name)}</div>
          <div class="nearby-meta">
            ${option.type === "bike" ? "Bike" : "Hub"} · ${formatDistance(option.distanceMeters)}
          </div>
        </button>
      `,
    )
    .join("");

  nearbyListElement.querySelectorAll(".nearby-button").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.dataset.nearbyIndex);
      const destination = nearbyOptions[index];

      if (destination) {
        showDestinationDetails(destination);
      }
    });
  });
}

function distanceBetweenMeters(start, destination) {
  const earthRadiusMeters = 6371000;

  const lat1 = toRadians(start.latitude);
  const lat2 = toRadians(destination.latitude);
  const deltaLat = toRadians(destination.latitude - start.latitude);
  const deltaLon = toRadians(destination.longitude - start.longitude);

  const a =
    Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
    Math.cos(lat1) *
      Math.cos(lat2) *
      Math.sin(deltaLon / 2) *
      Math.sin(deltaLon / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return earthRadiusMeters * c;
}

function toRadians(degrees) {
  return degrees * (Math.PI / 180);
}

function formatDistance(distanceMeters) {
  const miles = distanceMeters / 1609.344;

  if (miles < 0.1) {
    return `${Math.round(distanceMeters)} meters`;
  }

  return `${miles.toFixed(2)} miles`;
}
