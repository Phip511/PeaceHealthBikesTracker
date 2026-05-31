const EUGENE_CENTER = [44.0521, -123.0868];
const DEFAULT_ZOOM = 13;

export function createMap(elementId) {
  const map = L.map(elementId).setView(EUGENE_CENTER, DEFAULT_ZOOM);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  return map;
}
