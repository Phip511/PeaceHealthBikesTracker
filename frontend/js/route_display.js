/*
File: route_display.js

Purpose:
    Implements route selection and route visualization for the Bike
    Finder Map feature. This module manages user start locations,
    browser geolocation, route generation, route display, and route
    clearing functionality.

System context:
    This file is part of the PeaceHealth Rides Availability and
    Navigation Dashboard frontend. It provides the routing behavior
    used when users select a bike or hub destination and request
    walking directions from their current location.

Creation date:
    May 2026

Initial author:
    Dacian Rapolla

Modification history:
    June 2026 - Dacian Rapolla - Added start location selection,
    browser geolocation support, OSRM walking route integration,
    straight-line fallback routing, route visualization, and
    route-clearing functionality.
*/

let startMarker = null;
let routeLine = null;

export function enableRouteDisplay(map, routeDetailsElement, onStartLocationSet) {
  map.on("click", (event) => {
    setStartLocation(
      map,
      routeDetailsElement,
      {
        latitude: event.latlng.lat,
        longitude: event.latlng.lng,
      },
      onStartLocationSet,
    );
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

      setStartLocation(map, routeDetailsElement, startLocation, onStartLocationSet);
      map.setView([startLocation.latitude, startLocation.longitude], 15);
    },
    () => {
      routeDetailsElement.textContent =
        "Could not access browser location. Click the map to choose a start location.";
    },
  );
}


export function setStartLocation(map, routeDetailsElement, startLocation, onStartLocationSet) {
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

  if (onStartLocationSet) {
    onStartLocationSet(startLocation);
  }
}


export async function displayRouteToDestination(map, routeDetailsElement, destination) {
  const startLocation = window.currentStartLocation;

  if (!startLocation) {
    routeDetailsElement.textContent =
      "No start location selected. Click the map or use browser location first.";
    return;
  }

  routeDetailsElement.textContent = "Loading walking route...";

  try {
    const route = await fetchWalkingRoute(startLocation, destination);
    drawRoute(map, route.coordinates);

    routeDetailsElement.innerHTML = `
      <p><span class="details-label">Destination:</span> ${escapeHtml(destination.name)}</p>
      <p><span class="details-label">Route type:</span> Walking route estimate</p>
      <p><span class="details-label">Distance:</span> ${formatDistance(route.distanceMeters)}</p>
      <p><span class="details-label">Estimated walk time:</span> ${formatDuration(route.durationSeconds)}</p>
      <p>Walking routes are estimates based on OpenStreetMap/OSRM routing data. Campus 
      paths may be incomplete. Follow posted signs and avoid restricted or private areas.</p>
    `;
  } catch (error) {
    console.error(error);

    const fallback = buildStraightLineRoute(startLocation, destination);
    drawRoute(map, fallback.coordinates);

    routeDetailsElement.innerHTML = `
      <p><span class="details-label">Destination:</span> ${escapeHtml(destination.name)}</p>
      <p><span class="details-label">Route type:</span> Straight-line fallback</p>
      <p><span class="details-label">Approx. distance:</span> ${formatDistance(fallback.distanceMeters)}</p>
      <p>Walking routing could not be loaded, so this line does not follow streets or paths. 
      Follow posted signs and avoid restricted or private areas.</p>
    `;
  }
}

export function clearRoute(map, routeDetailsElement) {
  if (routeLine) {
    map.removeLayer(routeLine);
    routeLine = null;
  }

  routeDetailsElement.textContent =
    "Route cleared. Choose a start location, then select a bike or hub.";
}

async function fetchWalkingRoute(startLocation, destination) {
  const coordinates = [
    `${startLocation.longitude},${startLocation.latitude}`,
    `${destination.longitude},${destination.latitude}`,
  ].join(";");

  const url =
    `https://router.project-osrm.org/route/v1/foot/${coordinates}` +
    "?overview=full&geometries=geojson&steps=false";

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`OSRM request failed with status ${response.status}`);
  }

  const json = await response.json();

  if (!json.routes || !json.routes.length) {
    throw new Error("OSRM did not return a route.");
  }

  const route = json.routes[0];

  return {
    distanceMeters: route.distance,
    durationSeconds: route.duration,
    coordinates: route.geometry.coordinates.map(([longitude, latitude]) => [
      latitude,
      longitude,
    ]),
  };
}

function drawRoute(map, coordinates) {
  if (routeLine) {
    map.removeLayer(routeLine);
  }

  routeLine = L.polyline(coordinates, {
    weight: 4,
    opacity: 0.85,
  }).addTo(map);

  map.fitBounds(routeLine.getBounds(), {
    padding: [40, 40],
  });
}

function buildStraightLineRoute(startLocation, destination) {
  const coordinates = [
    [startLocation.latitude, startLocation.longitude],
    [destination.latitude, destination.longitude],
  ];

  return {
    coordinates,
    distanceMeters: distanceBetweenMeters(startLocation, destination),
  };
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

function formatDistance(distanceMeters) {
  const miles = distanceMeters / 1609.344;

  if (miles < 0.1) {
    return `${Math.round(distanceMeters)} meters`;
  }

  return `${miles.toFixed(2)} miles`;
}

function formatDuration(durationSeconds) {
  const minutes = Math.round(durationSeconds / 60);

  if (minutes < 1) {
    return "Less than 1 minute";
  }

  if (minutes === 1) {
    return "1 minute";
  }

  return `${minutes} minutes`;
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
