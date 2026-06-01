# PeaceHealth Rides Availability and Navigation Dashboard

## Project Overview

The PeaceHealth Rides Availability and Navigation Dashboard is a browser-based web application designed to help users locate currently available PeaceHealth Rides bikes and hubs in the Eugene/Springfield area.

The system uses public GBFS bike-share data to display bike and hub locations on a map. Users can select a starting location, view nearby bikes or hubs, and get basic direction or route information to the selected destination.

This project does **not** replace the official PeaceHealth Rides app. It does not support account creation, payment, bike reservation, unlocking, trip management, or private user account features. Its purpose is to provide a lightweight public availability and navigation dashboard.

## Authors / Contributors

| Name | Role / Contribution |
|---|---|
| Drew Moulton | [Role / Contribution] |
| Peyton Phillips | [Role / Contribution] |
| Dacian Rapolla | [Role / Contribution] |
| Jack Sedillos | [Role / Contribution] |

## Installation Instructions

Install Docker Desktop, then run the application from the project root:

```bash
docker compose up --build
```

Local access points:
```
Frontend: http://localhost:8080
Backend API: http://localhost:8000
```

## File Structure
```
peacehealth-bike-dashboard/
│
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   │
│   │   ├── api/
│   │   │   ├── routes_bikes.py
│   │   │   ├── routes_hubs.py
│   │   │   ├── routes_alerts.py
│   │   │   ├── routes_nearby.py
│   │   │   ├── routes_routes.py
│   │   │   └── routes_status.py
│   │   │
│   │   ├── services/
│   │   │   ├── ride_feed_collector.py
│   │   │   ├── ride_data_normalizer.py
│   │   │   ├── availability_query_service.py
│   │   │   ├── route_guidance_service.py
│   │   │   └── status_fallback_service.py
│   │   │
│   │   ├── models/
│   │   │   ├── bike_location.py
│   │   │   ├── hub_location.py
│   │   │   ├── system_alert.py
│   │   │   ├── route_summary.py
│   │   │   └── system_status.py
│   │   │
│   │   ├── data/
│   │   │   ├── sample/
│   │   │   │   ├── gbfs.json
│   │   │   │   ├── free_bike_status.json
│   │   │   │   ├── station_information.json
│   │   │   │   ├── station_status.json
│   │   │   │   └── system_alerts.json
│   │   │   │
│   │   │   └── cache/
│   │   │       └── .gitkeep
│   │   │
│   │   └── utils/
│   │       ├── distance.py
│   │       ├── json_loader.py
│   │       └── validation.py
│   │
│   └── tests/
│       ├── test_feed_collector.py
│       ├── test_data_normalizer.py
│       ├── test_availability_query.py
│       ├── test_distance.py
│       └── test_api_status.py
│
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── index.html
│   ├── css/
│   │   └── styles.css
│   └── js/
│       ├── app.js
│       ├── api_client.js
│       ├── map_view.js
│       ├── marker_renderer.js
│       ├── location_input.js
│       ├── route_display.js
│       └── status_banner.js
│
├── docs/
│   ├── SRS.md
│   ├── SDS.md
│   └── user_interviews/
│       └── interview_notes_template.md
│
└── scripts/
    ├── run_tests.sh
    ├── seed_sample_data.sh
    └── check_installation.sh
```

## File Structure Explanation

The root directory contains project-wide configuration files and documentation

| File | Purpose |
|---|---|
| README.md | Main project overview, setup notes, file structure, and contribution guidelines.
| docker-compose.yml | Runs the backend and frontend Docker containers together. |
| .env.example | Template for environment variables used by the project |
| .gitignore | lists files and folders that should not be commited to Git

## Backend

The backend/ folder contains the FastAPI server It is responsible for retrieving public GBFS data, normalizing bike-share information, calculating nearby bikes or hubs, and serving API responses to the frontend

## Frontend

The frontend folder contains frontend behavior split into smaller modules.

## Docs

The docs/ folder contains project documentation.

## Git Commit Message Guidelines

Use clear, structured comit messages so teammates can understand what changed and why.

Recommended format: 
```python
# <type>(<scope>): <short summary>
```

Example:
```python
# feat(api): add endpoint for nearby bikes
```

## Commit Types
|Type|Meaning|Example|
| --- | --- | --- |
| add | adds a singular new file | add(~/): README.md |
| ADD | adds multiple files / directories| ADD: added directories|
| RM | remove files / directories | RM: autosave files *~
| feat | Adds a new feature | feat(map): add bike markers |
| fix | fixes a bug | fix(api): handle missing station status feed |
| docs | Updates documentation | docs(readme): add Docker setup notes |
| style | changes formatting only | style(frontend): clean CSS indentation
| refactor | Reworks code without changing behavior | refactor(services): split feed parsing logic |
| test | Adds or updates tests | test(distance): add coordinate distance tests |
| chore | maintenance or setup work | chore(docker): update compose file |
| config | changes configuration files| config(env): add sample mode variable|

## Commit notes

Try to commit smaller steps rather than large chunks just to keep track of stuff easier.

## Live, Cached, and Sample Data Behavior

The dashboard can report three data modes: live, cached, and sample.

**Live Data** means the backend successfully loaded current PeaceHealth Rides GBFS data from the public feed. This is the preferred mode and is shown in the frontend as live availability data.

**Cached Data** means the live feed could not be refreshed, but the backend has a previously successful feed response stored locally. Cached data may be stale, so the frontend labels it clearly and warns the user that current bike availability may have changed.

**Sample Data** means the system is using local demonstration JSON files from the repository. Sample data is intended for testing, installation checks, and demos when live data is unavailable. It does not represent current PeaceHealth Rides availability.

The `/api/status` endpoint reports the current data source, source label, feed availability, last successful update time, and any fallback warnings. The frontend uses this information to show whether the dashboard is displaying live, cached, or sample data.

The `/api/dashboard` endpoint includes this status information along with normalized bikes, hubs, alerts, and freshness metadata.
