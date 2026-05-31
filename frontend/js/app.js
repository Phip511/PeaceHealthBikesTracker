import { fetchDashboardSnapshot } from "./api_client.js";
import { createMap } from "./map_view.js";
import { renderBikeMarkers, renderHubMarkers } from "./marker_renderer.js";

const map = createMap("map");

const dataStatusElement = document.querySelector("#data-status");
const bikeCountElement = document.querySelector("#bike-count");
const hubCountElement = document.querySelector("#hub-count");

loadDashboard();

async function loadDashboard() {
  try {
    const snapshot = await fetchDashboardSnapshot();

    renderBikeMarkers(map, snapshot.bikes || []);
    renderHubMarkers(map, snapshot.hubs || []);

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
