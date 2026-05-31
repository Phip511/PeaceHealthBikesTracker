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

enableRouteDisplay(map, routeDetailsElement);

useLocationButton.addEventListener("click", () => {
  useBrowserLocation(map, routeDetailsElement);
});

clearRouteButton.addEventListener("click", () => {
  clearRoute(map, routeDetailsElement);
});

loadDashboard();

async function loadDashboard() {
  try {
    const snapshot = await fetchDashboardSnapshot();

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
  } catch (error) {
    console.error(error);
    dataStatusElement.textContent = "Could not load dashboard data.";
    dataStatusElement.className = "status-pill error";

    freshnessDetailsElement.innerHTML = `
      <p><span class="details-label">Status:</span> <span class="source-error">Error</span></p>
      <p>Could not load freshness information.</p>
    `;
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
