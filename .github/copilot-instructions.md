# Copilot Instructions — 5G Network Quality Dashboard

## Project Overview

A full-stack AI engineering final project (COS40007) that visualises 5G network coverage quality
on a map and forecasts throughput over time. The ML pipeline is built in Python; the dashboard is
a Vue 3 SPA backed by a FastAPI service, orchestrated with Docker Compose.

---

## Core Stack

| Layer | Technology | Version |
|---|---|---|
| Frontend framework | Vue 3 (Composition API, `<script setup>`) | ^3.5 |
| Frontend build | Vite | ^6 |
| CSS framework | **Tailwind CSS v4** (Vite-native, `@tailwindcss/vite` plugin) | ^4 |
| Font | **Inter** (loaded via Google Fonts CDN in `index.html`) | — |
| Map | Leaflet + GeoJSON | ^1.9 |
| Chart | Apache ECharts | ^6 |
| HTTP client | Axios | ^1 |
| State management | Pinia | ^3 (scaffold only — not yet used for dashboard state) |
| Routing | Vue Router | ^5 (scaffold only — single-page dashboard, no routes yet) |
| Backend framework | **FastAPI** | latest in requirements.txt |
| Backend server | **Uvicorn** | latest |
| ML / data | scikit-learn, pandas, numpy | latest |
| Containerisation | **Docker Compose v2** (no `version:` key) | — |

---

## Repository Structure

```
AI4Eng_Theme5/
├── .github/
│   └── copilot-instructions.md   ← YOU ARE HERE
├── docker-compose.yml
├── README.md
├── backend/
│   ├── Dockerfile                ← python:3.10-slim, uvicorn :8000
│   ├── main.py                   ← re-exports: from app.main import app
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       └── main.py               ← all FastAPI routes + data helpers (single file currently)
│   data/                         ← cleaned CSV inputs (currently empty → fallback mock data used)
│   metrics/                      ← forecast CSV outputs (currently empty → fallback mock data)
│   models/                       ← trained .pkl / .h5 artifacts (currently empty)
└── frontend/
    ├── Dockerfile                ← multi-stage: node:20 build → nginx:stable-alpine :80
    ├── index.html                ← lang="vi", Inter font, title set
    ├── vite.config.ts            ← @tailwindcss/vite plugin registered
    └── src/
        ├── main.ts               ← imports src/assets/main.css (Tailwind entry)
        ├── assets/
        │   └── main.css          ← @import "tailwindcss"; + CSS custom properties
        └── App.vue               ← single-file dashboard component
```

---

## Architectural Constraints

1. **Single-component dashboard**: All UI logic lives in `src/App.vue`. Do not introduce new
   Vue components unless a piece of UI is reused in 3+ places.

2. **No new routes**: The app is intentionally a single-page dashboard. Do not add Vue Router
   routes without explicit user confirmation.

3. **Backend is single-module for now**: All FastAPI logic lives in `backend/app/main.py`.
   Refactoring into `routers/` / `services/` / `schemas/` is scoped to **Phase 2** only.

4. **Fallback data is intentional**: When `backend/data/` or `backend/metrics/` CSVs are absent
   the backend serves hard-coded mock rows. Do not remove this fallback — it keeps the dashboard
   renderable before the ML pipeline produces real outputs.

5. **Tailwind v4 conventions**: Use the `@tailwindcss/vite` plugin (no `tailwind.config.js`
   needed for defaults). Custom tokens go in `src/assets/main.css` as `@theme` variables, not in
   a config file. Do NOT use Tailwind v3 `tailwind.config.js` / `content:` patterns.

6. **No CSS-in-JS, no Sass**: All styling is Tailwind utility classes + scoped `<style>` blocks
   in `.vue` files where Tailwind cannot reach (e.g., third-party library overrides for Leaflet
   or ECharts). Do not introduce styled-components, emotion, or a Sass preprocessor.

---

## CORS / Networking Rules

### Development (local Docker Compose)
- Backend runs on `:8000`, frontend on `:8080` (nginx serving the Vite build).
- Frontend `VITE_API_BASE_URL` defaults to `http://localhost:8000` when the env var is not set.
- Backend CORS is currently `allow_origins=["*"]` — acceptable for local dev only.

### Production constraints (to be addressed in Phase 3)
- **CORS must be locked down** to the specific frontend origin. `allow_origins=["*"]` is
  forbidden in any environment accessible outside localhost.
- The preferred production pattern is an **nginx reverse-proxy**: the frontend nginx container
  proxies `/api/` requests to the backend service name (`backend:8000`) on the internal Docker
  network. This eliminates the cross-origin problem entirely and avoids exposing the backend port.
- If a proxy is not used, `VITE_API_BASE_URL` must be injected as a Docker build-arg so the
  Vite bundle references the correct public hostname — `http://localhost:8000` will not resolve
  from inside a Docker container.
- Do NOT hardcode any credential, API key, or internal hostname in frontend source files.

---

## API Contract (current)

```
GET /
  → { "message": "5G Network Quality API is running." }

GET /api/map-data
  → GeoJSON FeatureCollection
    features[].geometry.coordinates = [longitude, latitude]
    features[].properties = { square_id: string, quality: "Tot"|"Trung binh"|"Yeu" }

GET /api/forecast-data
  → { time: string[], predicted_speed_mbps: number[] }
```

Quality label mapping (Vietnamese):
- `"Tot"` → Good (green `#17a34a`)
- `"Trung binh"` → Medium (amber `#f59e0b`)
- `"Yeu"` → Poor (red `#dc2626`)

---

## Finalized Cloud Architecture (AWS + Supabase)

### Authentication
- Developers access a hidden `/admin` route on the frontend.
- **Supabase** handles authentication and issues a JWT.
- FastAPI verifies the Supabase JWT before serving protected data or accepting uploads.

### Serving Layer
- **CloudFront** serves the Vue 3 frontend as a static site.
- **AWS API Gateway + AWS Lambda (via Mangum)** hosts the FastAPI backend as a serverless function.

### MLOps Pipeline (Continuous Training)
1. Authenticated developer uploads a new 5G CSV → **S3 Raw Data**.
2. An S3 Event triggers a **single AWS Lambda function**.
3. Lambda triggers **Amazon SageMaker Pipelines** (the orchestrator).
4. SageMaker runs a **Processing Job**: cleans invalid 99999 coordinates / 1000 timeouts,
   merges cleaned data with the historical Feature Store in **S3 Cleaned Data**.
5. SageMaker runs a **Training Job**: K-Means clustering + time-series forecasting on a
   rolling window of recent data. Evaluates new Challenger vs current Champion model.
6. Approved `.pkl` model artifacts are versioned and stored in **S3 Artifacts**.

### Inference Flow (Live Dashboard)
1. User accesses the 5G Dashboard via **CloudFront CDN**.
2. If accessing backend tools, **Supabase** verifies identity and issues JWT.
3. Vue app calls `/api`. CloudFront routes API requests to **API Gateway**, which triggers the **Lambda container** (Mangum wrapper) running FastAPI to verify tokens and handle the request.
4. FastAPI (inside Lambda) dynamically loads the latest approved models from **S3 Artifacts** into memory.
5. Backend runs inference, returning GeoJSON and forecast arrays to the UI.

---

## 5-Phase Development Plan

### Phase 0 — Frontend UI/UX Foundation ✅ (implement first)
- Install Tailwind CSS v4 (`@tailwindcss/vite`) and Inter font
- Global CSS base: reset, custom properties, antialiasing
- Responsive 3-state layout (mobile / tablet / desktop)
- Top navbar: project icon + title + API status badge
- Panel cards: shadow, accent border, consistent padding
- Map quality legend (Tot / Trung binh / Yeu colour dots)
- Loading skeleton (CSS shimmer animation)
- Error banner with Retry button
- Accessibility: `lang`, `aria-live`, focus-visible rings

### Phase 1 — Data & Model Pipeline
- `backend/scripts/train.py`: preprocessing + model training
- Clustering model for map quality labels → save to `backend/models/`
- Time-series forecasting model → save forecast CSV to `backend/metrics/`
- Cleaned input CSV → save to `backend/data/`

### Phase 2 — Backend Refactor
- Split `backend/app/main.py` into:
  - `routers/map.py`, `routers/forecast.py`
  - `services/data_loader.py`
  - `schemas/responses.py`
- Load model artifacts at FastAPI startup (`lifespan` context)
- Tighten CORS to specific allowed origins

### Phase 3 — Docker Hardening
- `docker-compose.dev.yml` override for hot-reload dev workflow
- Inject `VITE_API_BASE_URL` via build-arg OR configure nginx `/api/` proxy
- Add `healthcheck:` to both services in `docker-compose.yml`
- Pin all image versions (python, node, nginx)

### Phase 4 — Testing
- `backend/tests/`: pytest unit tests for data helpers and all endpoints
- Expand `frontend/cypress/e2e/` spec: map renders, chart renders, error state, retry button

---

## Coding Conventions

- **Python**: type-annotated function signatures, `Path` objects for filesystem ops, no bare
  `except:` clauses.
- **TypeScript/Vue**: `<script setup lang="ts">` always; explicit type annotations on `ref<T>`,
  `computed<T>`, and function parameters; no `any`.
- **Commits**: conventional commits style (`feat:`, `fix:`, `chore:`, `style:`, `test:`).
- **No commented-out code**: remove dead code rather than leaving it commented.
