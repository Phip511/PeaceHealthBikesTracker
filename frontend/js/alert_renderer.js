let alertMarkers = [];

export function renderAlerts(map, alerts, alertsPanelElement) {
  clearAlertMarkers(map);

  if (!alerts || alerts.length === 0) {
    alertsPanelElement.innerHTML = "<p>No active system alerts.</p>";
    return;
  }

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

  alerts.forEach((alert) => {
    if (!alert.affected_station_ids) {
      return;
    }

    alert.affected_station_ids.forEach((stationId) => {
      const stationMarker = window.hubLookup?.[stationId];

      if (!stationMarker) {
        return;
      }

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

      alertMarkers.push(marker);
    });
  });
}

function clearAlertMarkers(map) {
  alertMarkers.forEach((marker) => map.removeLayer(marker));
  alertMarkers = [];
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
