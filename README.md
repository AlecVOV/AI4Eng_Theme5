# 5G Network Quality Dashboard

A full-stack AI engineering dashboard for visualising 5G network coverage quality on a map and forecasting throughput over time.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Uvicorn (`:8000`) |
| Frontend | Vue 3 + Vite + Tailwind CSS v4 + Leaflet + ECharts (`:5173` dev / `:8080` Docker) |
| ML | scikit-learn (KMeans) + XGBoost (forecasting) |
| Auth | Supabase (email/password → JWT) |
| Orchestration | Docker Compose v2 |

---

## Prerequisites

- **Python** 3.10+
- **Node.js** 20+
- **Docker** & **Docker Compose** (for containerised run)

---

## Option 1 — Run Backend & Frontend Individually

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

### Frontend

Open a **second terminal**:

```bash
cd frontend
npm install
npm run dev
```

The dev server will be available at `http://localhost:5173`.

> The frontend defaults `VITE_API_BASE_URL` to `http://localhost:8000` so it will connect to the backend automatically.

---

## Option 2 — Run Everything with Docker Compose

From the project root:

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

---

## Access URLs

| Service | Local Dev | Docker Compose |
|---|---|---|
| Frontend Dashboard | `http://localhost:5173` | `http://localhost:8080` |
| Backend API | `http://localhost:8000` | `http://localhost:8000` |
| Swagger Docs | `http://localhost:8000/docs` | `http://localhost:8000/docs` |

---

## Available API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/api/map-data` | Cluster map data (`lat`, `lng`, `cluster`) |
| `GET` | `/api/forecast-data` | Forecast series (`timestamp`, `predicted_throughput`, `predicted_latency`) |
| `POST` | `/api/contact` | Send feedback email via Resend |

---

## Data / Model Folders

- `backend/data/` — raw 5G CSVs + `map_data.csv` (clustering output)
- `backend/metrics/` — `forecast_data.csv` (forecasting output)
- `backend/models/` — trained model artifacts (`.pkl`, `.h5`)

If CSV files are missing or schema is incomplete, backend automatically uses fallback mock data so the dashboard can still render.
