# User Guide

After starting the application with Docker Compose, open the dashboard in a web
browser:

```text
http://localhost:8080
```

The dashboard shows public PeaceHealth Rides bike and hub availability on a map.
Bike markers represent available bikes. Hub markers represent stations or hubs
with availability information.

## Checking Data Status

The status label at the top of the page reports which data source is active:

| Status | Meaning |
|---|---|
| Live Data | The backend loaded current public GBFS data. |
| Cached Data | Live data could not be refreshed, so the backend is showing the most recent cached feed data. |
| Sample Data | The backend is showing local demonstration data. This is useful for testing but does not represent current availability. |

The Data Freshness panel shows the last update time, whether live data is
available, whether cached data is available, and whether sample data is
available.

## Finding a Bike or Hub

1. Review the bike and hub markers on the map.
2. Click a bike or hub marker to view its details in the Selected Destination
   panel.
3. Use the Loaded Data panel to confirm how many bikes and hubs were loaded.

## Choosing a Start Location

To see nearby options or route information, choose a start location:

1. Click anywhere on the map, or
2. Click **Use my location** and allow browser location access.

After a start location is selected, the Nearby Options panel lists the closest
available bikes and hubs based on map distance.

## Viewing a Route

After choosing a start location, click a bike or hub marker or choose an item in
Nearby Options. The Route panel shows an estimated walking route, distance, and
walk time when routing data is available.

Walking routes are estimates based on OpenStreetMap and OSRM routing data. If
route data cannot be loaded, the dashboard falls back to a straight-line
distance estimate.

## System Alerts

If the public GBFS feed includes system alerts, they appear in the System Alerts
panel. Alerts may describe station closures, service notices, or other public
system information.

## Troubleshooting

If the dashboard does not load data, confirm the containers are running:

```bash
docker compose ps
```

Then confirm the backend is responding:

```text
http://localhost:8000/api/status
```

If live data is unavailable, the dashboard should fall back to cached or sample
data. Sample data is enough to verify that the application is working.

If the map or walking route does not appear, confirm that the computer has
internet access. The dashboard uses external map tiles and routing services for
map display and walking route estimates.

This dashboard only displays public availability and navigation information. Use
the official PeaceHealth Rides app for account, payment, reservation, unlocking,
and trip management actions.
