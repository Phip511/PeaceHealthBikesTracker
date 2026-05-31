import { fetchDashboardSnapshot } from "./api_client.js";
import { createMap } from "./map_view.js";
import { renderBikeMarkers, renderHubMarkers } from "./marker_renderer.js";

const map = createMap("map");

const dataStatusElement = document.querySelector("#data-status");
const bikeCountElement = document.querySelector("#bike-count");
const hubCountElement = document.querySelector("#hub-count");
const destinationDetailsElement = document.querySelector("#destination-details");

loadDashboard();

async function loadDashboard() {
  try {
    const snapshot = await fetchDashboardSnapshot();

    renderBikeMarkers(map, snapshot.bikes || [], showDestinationDetails);
    renderHubMarkers(map, snapshot.hubs || [], showDestinationDetails);

    updateCounts(snapshot);
    updateStatus(snapshot.status);
  } catch (error) {
    console.error(error);
    dataStatusElement.textContent = "Could not load dashboard data.";
    dataStatusElement.className = "status-pill error";
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
