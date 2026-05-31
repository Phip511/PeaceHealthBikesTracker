let startMarker = null;
let routeLine = null;

export function enableRouteDisplay(map, routeDetailsElement) {
  map.on("click", (event) => {
    setStartLocation(map, routeDetailsElement, {
      latitude: event.latlng.lat,
      longitude: event.latlng.lng,
    });
  });
}

export function useBrowserLocation(map, routeDetailsElement, onStartLocationSet) {
  if (!navigator.geolocation) {
    routeDetailsElement.textContent = "Browser geolocation is not available.";
    return;
  }

  routeDetailsElement.textContent = "Requesting browser location...";

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const startLocation = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
      };

      setStartLocation(map, routeDetailsElement, startLocation);
      map.setView([startLocation.latitude, startLocation.longitude], 15);

      if (onStartLocationSet) {
        onStartLocationSet(startLocation);
      }
    },
    () => {
      routeDetailsElement.textContent =
        "Could not access browser location. Click the map to choose a start location.";
    },
  );
}

export function setStartLocation(map, routeDetailsElement, startLocation) {
  window.currentStartLocation = startLocation;

  if (startMarker) {
    map.removeLayer(startMarker);
  }

  const startIcon = L.divIcon({
    className: "",
    html: '<div class="start-marker" aria-label="Start location marker"></div>',
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });

  startMarker = L.marker([startLocation.latitude, startLocation.longitude], {
    icon: startIcon,
  })
    .bindPopup("Start location")
    .addTo(map);

  routeDetailsElement.textContent =
    "Start location selected. Now choose a bike or hub destination.";
}

export function displayRouteToDestination(map, routeDetailsElement, destination) {
  const startLocation = window.currentStartLocation;

  if (!startLocation) {
    routeDetailsElement.textContent =
      "No start location selected. Click the map or use browser location first.";
    return;
  }

  if (routeLine) {
    map.removeLayer(routeLine);
  }

  const start = [startLocation.latitude, startLocation.longitude];
  const end = [destination.latitude, destination.longitude];

  routeLine = L.polyline([start, end], {
    weight: 4,
    opacity: 0.8,
  }).addTo(map);

  map.fitBounds(routeLine.getBounds(), {
    padding: [40, 40],
  });

  const distanceMeters = distanceBetweenMeters(startLocation, destination);
  const distanceMiles = distanceMeters / 1609.344;

  routeDetailsElement.innerHTML = `
    <p><span class="details-label">Destination:</span> ${escapeHtml(destination.name)}</p>
    <p><span class="details-label">Approx. straight-line distance:</span> ${distanceMiles.toFixed(2)} miles</p>
    <p>This is a simple route estimate, not turn-by-turn walking directions.</p>
  `;
}

export function clearRoute(map, routeDetailsElement) {
  if (routeLine) {
    map.removeLayer(routeLine);
    routeLine = null;
  }

  routeDetailsElement.textContent =
    "Route cleared. Choose a start location, then select a bike or hub.";
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

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
