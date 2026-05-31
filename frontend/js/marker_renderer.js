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

export function renderBikeMarkers(map, bikes) {
  const bikeIcon = createBikeIcon();

  bikes
    .filter((bike) => bike.is_available)
    .forEach((bike) => {
      L.marker([bike.latitude, bike.longitude], { icon: bikeIcon })
        .bindPopup(
          `<strong>Available Bike</strong><br>
           ID: ${bike.bike_id}<br>
           Last reported: ${formatTimestamp(bike.last_reported)}`
        )
        .addTo(map);
    });
}

export function renderHubMarkers(map, hubs) {
  const hubIcon = createHubIcon();

  hubs.forEach((hub) => {
    const availableText =
      hub.available_bikes === null || hub.available_bikes === undefined
        ? "Unknown"
        : hub.available_bikes;

    L.marker([hub.latitude, hub.longitude], { icon: hubIcon })
      .bindPopup(
        `<strong>${hub.name}</strong><br>
         Available bikes: ${availableText}<br>
         Last reported: ${formatTimestamp(hub.last_reported)}`
      )
      .addTo(map);
  });
}

function formatTimestamp(epochSeconds) {
  if (!epochSeconds) {
    return "Unknown";
  }

  return new Date(epochSeconds * 1000).toLocaleString();
}
