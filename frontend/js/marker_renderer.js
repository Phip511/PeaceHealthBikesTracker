/*
File: marker_renderer.js

Purpose:
    Creates and displays bike and hub markers on the dashboard map.
    This module is responsible for marker appearance, marker selection,
    popup content, and communication between map markers and the
    destination details panel.

System context:
    This file is part of the PeaceHealth Rides Availability and
    Navigation Dashboard frontend. It converts normalized bike and
    hub data into interactive Leaflet markers that users can select
    to view availability and routing information.

Creation date:
    May 2026

Initial author:
    Dacian Rapolla

Modification history:
    June 2026 - Dacian Rapolla - Added bike marker rendering, hub
    marker rendering, marker selection highlighting, popup support,
    and hub lookup support for system alerts.
*/

let activeMarkerElement = null;

window.hubLookup = {};

function createBikeIcon() {
  return L.divIcon({
    className: "",
    html: '<div class="marker-bike" aria-label="Available bike marker"></div>',
    iconSize: [16, 16],
    iconAnchor: [8, 8],
    popupAnchor: [0, -8],
  });
}

function createHubIcon() {
  return L.divIcon({
    className: "",
    html: '<div class="marker-hub" aria-label="Hub marker"></div>',
    iconSize: [18, 18],
    iconAnchor: [9, 9],
    popupAnchor: [0, -9],
  });
}

export function renderBikeMarkers(map, bikes, onMarkerSelected) {
  const bikeIcon = createBikeIcon();

  bikes
    .filter((bike) => bike.is_available)
    .forEach((bike) => {
      const marker = L.marker([bike.latitude, bike.longitude], { icon: bikeIcon })
        .bindPopup(
          `<strong>Available Bike</strong><br>
           ID: ${bike.bike_id}<br>
           Last reported: ${formatTimestamp(bike.last_reported)}`
        )
        .addTo(map);
      

      marker.on("click", () => {
        setActiveMarker(marker);

        onMarkerSelected({
          type: "bike",
          id: bike.bike_id,
          name: "Available Bike",
          latitude: bike.latitude,
          longitude: bike.longitude,
          availableBikes: null,
          lastReported: bike.last_reported,
        });
      });
    });
}

export function renderHubMarkers(map, hubs, onMarkerSelected) {
  window.hubLookup = {};

  const hubIcon = createHubIcon();

  hubs.forEach((hub) => {
    const availableText =
      hub.available_bikes === null || hub.available_bikes === undefined
        ? "Unknown"
        : hub.available_bikes;

    const marker = L.marker([hub.latitude, hub.longitude], { icon: hubIcon })
      .bindPopup(
        `<strong>${hub.name}</strong><br>
         Available bikes: ${availableText}<br>
         Last reported: ${formatTimestamp(hub.last_reported)}`
      )
      .addTo(map);

    window.hubLookup[hub.station_id] = marker;

    marker.on("click", () => {
      setActiveMarker(marker);

      onMarkerSelected({
        type: "hub",
        id: hub.station_id,
        name: hub.name,
        latitude: hub.latitude,
        longitude: hub.longitude,
        availableBikes: hub.available_bikes,
        lastReported: hub.last_reported,
      });
    });
  });
}

function setActiveMarker(marker) {
  if (activeMarkerElement) {
    activeMarkerElement.classList.remove("marker-selected");
  }

  const markerElement = marker.getElement();

  if (markerElement) {
    const visualMarker = markerElement.firstElementChild || markerElement;
    visualMarker.classList.add("marker-selected");
    activeMarkerElement = visualMarker;
  }
}

function formatTimestamp(epochSeconds) {
  if (!epochSeconds) {
    return "Unknown";
  }

  return new Date(epochSeconds * 1000).toLocaleString();
}
