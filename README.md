# 5G Network Quality Dashboard

A full-stack mock dashboard for visualizing 5G network quality.

## Tech Stack

- Backend: FastAPI (`:8000`)
- Frontend: Vue 3 + Vite + Leaflet + ECharts (`:8080`)
- Orchestration: Docker Compose

## Run Project

From project root:

```bash
docker compose up --build
```

Run in background:

```bash
docker compose up --build -d
```

Stop services:

```bash
docker compose down
```

## Access URLs

- Frontend Dashboard: `http://localhost:8080`
- Backend API: `http://localhost:8000`
- Swagger Docs: `http://localhost:8000/docs`

## Available API Endpoints

- `GET /api/map-data`
  - Returns GeoJSON points with `square_id`, `quality`, `latitude`, `longitude`.
- `GET /api/forecast-data`
  - Returns forecast series: `time[]` and `predicted_speed_mbps[]`.

## Data/Model Folders

- `backend/data/`: cleaned CSV input (mock-read by backend)
- `backend/metrics/`: CSV metrics/forecast output (mock-read by backend)
- `backend/models/`: trained model artifacts (`.pkl`, `.h5`)

If CSV files are missing or schema is incomplete, backend automatically uses fallback mock data so the dashboard can still render.
