/*
File: alert_renderer.js

Purpose:
    Renders public PeaceHealth Rides system alerts in the frontend
    sidebar and displays alert indicators on the map when alerts are
    associated with known hubs.

System context:
    This file is part of the PeaceHealth Rides Availability and
    Navigation Dashboard frontend. It uses normalized alert data from
    the /api/dashboard endpoint and coordinates with hub markers created
    by marker_renderer.js through the window.hubLookup table.

Creation date:
    May 2026

Initial author:
    Dacian Rapolla

Modification history:
    June 2026 - Dacian Rapolla - Added system alert sidebar rendering
    and map alert marker support.
*/

// Track alert markers currently displayed on the map so they can be
// removed before rendering a new alert set.
let alertMarkers = [];

// Render alert information in the sidebar and draw alert markers on
// affected hubs when the alert references known station IDs.
export function renderAlerts(map, alerts, alertsPanelElement) {
  // Remove old alert markers before drawing the current alert state.
  clearAlertMarkers(map);

  // If no alerts are available, display a simple empty-state message.
  if (!alerts || alerts.length === 0) {
    alertsPanelElement.innerHTML = "<p>No active system alerts.</p>";
    return;
  }

  // Render each alert as a readable sidebar item.
  alertsPanelElement.innerHTML = alerts
    .map(
      (alert) => `
        <div class="alert-item">
          <div class="alert-title">${escapeHtml(alert.summary)}</div>
          <div class="alert-description">
            ${escapeHtml(alert.description)}
          </div>
        </div>
      `
    )
    .join("");

  // For alerts that reference stations, place visual indicators around
  // the affected hub markers.
  alerts.forEach((alert) => {
    // Alerts without affected station IDs can still appear in the
    // sidebar, but cannot be attached to a map location.
    if (!alert.affected_station_ids) {
      return;
    }

    // Draw one map alert indicator for each affected station that has
    // a corresponding hub marker.
    alert.affected_station_ids.forEach((stationId) => {
      const stationMarker = window.hubLookup?.[stationId];

      // If the station is not currently displayed, skip map rendering
      // for that alert target.
      if (!stationMarker) {
        return;
      }

      // Draw a circular marker around the affected hub location.
      const marker = L.circleMarker(stationMarker.getLatLng(), {
        radius: 12,
        weight: 3,
        opacity: 1,
        fillOpacity: 0.15,
      })
        .bindPopup(
          `<strong>System Alert</strong><br>${escapeHtml(alert.summary)}`
        )
        .addTo(map);

      // Store the alert marker so it can be removed on the next render.
      alertMarkers.push(marker);
    });
  });
}

// Remove all alert markers currently displayed on the map.
function clearAlertMarkers(map) {
  alertMarkers.forEach((marker) => map.removeLayer(marker));
  alertMarkers = [];
}

// Escape HTML characters before inserting alert text into the page.
function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
