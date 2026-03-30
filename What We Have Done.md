# What We Have Done — Full Project Delivery Report

> **COS40007 — AI For Engineering (Final Project)**
> **Theme 5 — 5G Network Quality Dashboard**
> Swinburne University of Technology
>
> This document provides a complete record of every development session and deliverable produced
> from project inception through the latest session (31 Mar 2026).

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [Repository Structure](#repository-structure)
4. [Phase 0 — Frontend UI/UX Foundation](#phase-0--frontend-uiux-foundation)
5. [Phase 1 — Data & ML Model Pipeline](#phase-1--data--ml-model-pipeline)
6. [Backend API Development](#backend-api-development)
7. [Authentication & Admin Panel](#authentication--admin-panel)
8. [Resend Email Integration — Contact Form](#resend-email-integration--contact-form)
9. [Cloud Architecture Design](#cloud-architecture-design)
10. [Docker & DevOps](#docker--devops)
11. [Bug Fixes & Debugging Log](#bug-fixes--debugging-log)
12. [Current Project Status](#current-project-status)
13. [Complete File Inventory](#complete-file-inventory)

---

## Project Overview

The **5G Network Quality Dashboard** is a full-stack AI engineering project that:

1. **Collects** raw 5G drive-test telemetry data (GPS coordinates, throughput, latency, signal metrics) from garbage truck fleet sensors across the Brimbank area of Melbourne.
2. **Preprocesses** the data — cleaning invalid coordinates (99999), timeout values (1000), and merging multiple truck runs.
3. **Trains ML models** — KMeans clustering to classify geographic zones into 3 signal quality tiers (Tốt / Trung bình / Yếu) and XGBoost time-series forecasting for throughput and latency prediction.
4. **Serves predictions** through a FastAPI backend with structured JSON endpoints.
5. **Visualises results** on an interactive Vue 3 dashboard with a Leaflet map (colour-coded cluster markers) and Apache ECharts dual-axis forecast chart.
6. **Orchestrates** the full stack via Docker Compose for reproducible deployment.

**Data source:** 138 raw CSV files from garbage truck fleet 5G probes across 4 days (4–7 July 2022), plus 1 generated `map_data.csv` output from the clustering model.

---

## Technology Stack

### Frontend

| Technology | Version | Purpose |
|---|---|---|
| Vue 3 (Composition API, `<script setup lang="ts">`) | ^3.5 | SPA framework |
| Vite | ^7.3 | Build tool and dev server |
| Tailwind CSS v4 | ^4.2 | Utility-first CSS (via `@tailwindcss/vite` plugin) |
| Inter font | — | Typography (Google Fonts CDN) |
| Leaflet | ^1.9 | Interactive map with OpenStreetMap tiles |
| Apache ECharts | ^6.0 | Dual-axis throughput/latency chart |
| Axios | ^1.13 | HTTP client for API calls |
| Vue Router | ^5.0 | Client-side routing (7 routes) |
| Pinia | ^3.0 | State management (scaffolded, not yet actively used) |
| Supabase JS | ^2.100 | Authentication client |
| TypeScript | ~5.9 | Type safety across entire frontend |
| Cypress | ^15.11 | E2E testing framework |
| Vitest | ^4.0 | Unit testing framework |

### Backend

| Technology | Version | Purpose |
|---|---|---|
| FastAPI | latest | REST API framework |
| Uvicorn | latest | ASGI server |
| pandas | latest | Data loading and transformation |
| scikit-learn | latest | KMeans clustering model |
| XGBoost | latest | Time-series forecasting (throughput + latency) |
| Optuna | latest | Hyperparameter tuning |
| LightGBM / CatBoost | latest | Alternative model experimentation |
| Resend | latest | Transactional email API (contact form) |
| python-dotenv | latest | Environment variable management |
| Pydantic + email-validator | latest | Request/response validation |

### Infrastructure

| Technology | Purpose |
|---|---|
| Docker Compose v2 | Multi-service orchestration |
| python:3.10-slim | Backend container image |
| node:20-alpine → nginx:stable-alpine | Frontend multi-stage build |
| Supabase | Authentication (email/password → JWT) |
| AWS CloudFront, API Gateway, Lambda (Mangum), S3, SageMaker | Serverless production cloud architecture |

---

## Repository Structure

```
AI4Eng_Theme5/
├── .github/
│   └── copilot-instructions.md          ← AI coding assistant rules
├── docker-compose.yml                   ← Orchestrates backend + frontend
├── README.md                            ← Quick-start guide
├── What We Have Done.md                 ← THIS FILE — full project report
│
├── backend/
│   ├── Dockerfile                       ← python:3.10-slim, uvicorn :8000
│   ├── main.py                          ← Re-export: from app.main import app
│   ├── requirements.txt                 ← 32 Python dependencies
│   ├── .env                             ← RESEND_API_KEY + CONTACT_TO_EMAIL
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py                      ← All FastAPI routes + data helpers (150 lines)
│   ├── data/
│   │   ├── map_data.csv                 ← Clustering output (lat, lng, cluster)
│   │   └── 138 raw CSV files            ← 5G drive-test telemetry (garbo01–garbo11, 4 days)
│   ├── metrics/
│   │   └── forecast_data.csv            ← Forecasting output (timestamp, throughput, latency)
│   ├── models/
│   │   ├── clustering_model.pkl         ← Trained KMeans model
│   │   ├── clustering_scaler.pkl        ← StandardScaler for clustering features
│   │   ├── pipeline_config.pkl          ← Pipeline configuration artifact
│   │   ├── xgboost_download_mbps.pkl    ← XGBoost throughput forecaster
│   │   ├── xgboost_avg_latency.pkl      ← XGBoost latency forecaster
│   │   └── forecasting_model.h5         ← Alternative deep learning model
│   ├── 1_data_preprocessing.ipynb       ← Notebook: data cleaning & EDA
│   ├── 2_model_clustering.ipynb         ← Notebook: KMeans training
│   └── 3_model_forecasting.ipynb        ← Notebook: XGBoost forecasting
│
└── frontend/
    ├── Dockerfile                       ← Multi-stage: node:20 → nginx:stable-alpine :80
    ├── index.html                       ← lang="vi", Inter font, SVG favicon
    ├── package.json                     ← 7 dependencies + 18 devDependencies
    ├── vite.config.ts                   ← @tailwindcss/vite plugin registered
    └── src/
        ├── main.ts                      ← App bootstrap, imports main.css
        ├── App.vue                      ← Root layout: navbar + RouterView + footer (93 lines)
        ├── assets/
        │   ├── main.css                 ← Tailwind v4 entry + @theme custom properties (34 lines)
        │   ├── AWSArchitecture.png      ← Static architecture diagram
        │   └── AWSArchitecture.svg      ← Vector version of architecture diagram
        ├── components/
        │   ├── AWSArchitectureMap.vue   ← Interactive cloud infra explorer (240 lines)
        │   ├── MLOpsPipeline.vue        ← Animated MLOps pipeline timeline (276 lines)
        │   └── FooterComp.vue           ← Global footer with nav + branding (77 lines)
        ├── views/
        │   ├── DashboardView.vue        ← Main dashboard: map + chart (283 lines)
        │   ├── AboutView.vue            ← Team member cards with animations (192 lines)
        │   ├── ArchitectureView.vue     ← Architecture page: problem, stack, roadmap (229 lines)
        │   ├── ContactView.vue          ← Contact form + social links (245 lines)
        │   ├── AdminView.vue            ← Protected admin panel (226 lines)
        │   ├── LoginView.vue            ← Supabase sign-in page (114 lines)
        │   └── NotFoundView.vue         ← 404 page (26 lines)
        ├── router/
        │   └── index.ts                 ← 7 routes + Supabase auth guard (54 lines)
        ├── services/
        │   ├── supabase.ts              ← Supabase client initialisation (6 lines)
        │   └── mockData.ts              ← Type definitions + seeded mock generators (99 lines)
        └── stores/
            └── counter.ts               ← Pinia scaffold (unused)
```

---

## Phase 0 — Frontend UI/UX Foundation

> **Status: ✅ Complete**

### 0a. Tailwind CSS v4 Setup

- Installed `tailwindcss` ^4.2 and `@tailwindcss/vite` ^4.2 as dev dependencies.
- Registered the `tailwindcss()` plugin in `vite.config.ts` (no `tailwind.config.js` needed — Tailwind v4 convention).
- Created `src/assets/main.css` with:
  - `@import "tailwindcss";` (v4 entry point)
  - `@theme` block defining custom design tokens: `--font-sans` (Inter), brand colours (green/amber/red/teal), surface/panel/border/text semantic tokens.
  - Global reset: `box-sizing: border-box`, font smoothing, body margin reset.

### 0b. Inter Font Integration

- Added Google Fonts CDN links in `index.html` with `rel="preconnect"` for performance.
- Set `lang="vi"` on `<html>` for Vietnamese language support.
- Added `<meta name="description">` for SEO.

### 0c. App Shell — App.vue (93 lines)

- **Sticky top navbar** with:
  - Brand logo (teal 5G signal tower SVG) + "5G Dashboard" text.
  - Desktop navigation: 5 `RouterLink` items with active-state highlighting (teal background).
  - Mobile hamburger menu with animated open/close icons.
  - `backdrop-blur-sm` glass effect on scroll.
- **`<RouterView />`** for page content.
- **Global footer** via `FooterComp.vue`.

### 0d. FooterComp.vue — Created (77 lines)

- Dark `bg-gray-900` footer with two-column layout.
- Left column: Brand icon, project description, university attribution.
- Right column: Navigation links matching the navbar.
- Bottom bar: copyright notice with dynamic year.

### 0e. DashboardView.vue — Main Dashboard (283 lines)

The primary page of the application. Contains:

**Data fetching:**
- Parallel `axios.get()` calls to `/api/map-data` and `/api/forecast-data`.
- `VITE_API_BASE_URL` env var support (defaults to `http://localhost:8000`).
- Comprehensive error handling with Axios error detection, status codes, and detail messages.

**Map panel (Leaflet):**
- OpenStreetMap tile layer, centred on Brimbank, Melbourne (-37.755, 144.845).
- `L.circleMarker` for each data point with colour-coded clusters:
  - Cluster 0 = Yếu (Poor) → red `#dc2626`
  - Cluster 1 = Trung bình (Medium) → amber `#f59e0b`
  - Cluster 2 = Tốt (Good) → green `#17a34a`
- Popup on click showing cluster label and coordinates.
- Auto `fitBounds()` with 15% padding.
- Quality legend bar at the bottom.

**Chart panel (Apache ECharts):**
- Dual-axis line chart:
  - Left Y-axis: Throughput (Mbps) — solid teal line with area fill.
  - Right Y-axis: Latency (ms) — dashed amber line.
- Tooltip with cross-axis pointer.
- Responsive: resizes on window resize events.

**UX states:**
- **Loading:** Two skeleton shimmer cards (CSS animation).
- **Error:** Red alert banner with error detail + "Retry" button.
- **Success:** Two-column grid (responsive to single column on mobile).

**Accessibility:**
- `aria-busy`, `aria-label`, `aria-live="assertive"` on error banner.
- `role="alert"` on error messages.
- `focus-visible` outline on retry button.

### 0f. AboutView.vue — Team Page (192 lines)

- Hero section with "COS40007 Final Project" badge.
- 4 team member cards with:
  - Avatar placeholder (coloured initials badge).
  - Role badge (ML Engineer, Backend Developer, Frontend Developer, Data Analyst).
  - School, major, bio text.
  - "Key Contributions" list with check-mark icons.
- **Scroll reveal animation:** `IntersectionObserver` triggers `translateY` + `opacity` transition on each card as it enters the viewport.

### 0g. ArchitectureView.vue — Architecture Page (229 lines)

A comprehensive architecture documentation page with 5 sections:

1. **The Problem** — Three problem cards (Coverage Gaps, Throughput Prediction, Real-Time Visibility) with icon illustrations.
2. **System Architecture** — Embedded `MLOpsPipeline.vue` animated component.
3. **Interactive Cloud Infrastructure Explorer** — Embedded `AWSArchitectureMap.vue` component.
4. **Complete System Architecture** — Static `AWSArchitecture.png` diagram.
5. **Technology Stack** — 2×2 grid of layer cards (Frontend, API Layer, ML Pipeline, Infrastructure) with item details.
6. **Development Roadmap** — Vertical timeline showing all 5 phases with tech tags.

### 0h. ContactView.vue — Contact Page (245 lines)

- Two-column layout: contact form (3/5 width) + links sidebar (2/5 width).
- **Form:** Full name, email, message fields with client-side validation.
- **Success state:** Green confirmation card with "Send another message" button.
- **Error state:** Red inline error banner.
- **Links sidebar:** GitHub repository, LinkedIn, Email — each as a styled card with SVG icons.
- **Course tag:** "COS40007 — AI For Engineering, Swinburne University" info box.

### 0i. NotFoundView.vue — 404 Page (26 lines)

- Large orange "404" number.
- Thematic message: "Oops! The zone you are looking for has no 5G coverage."
- "Return to Dashboard" button with back-arrow icon.

### 0j. Favicon — Custom SVG

- Created `frontend/public/favicon.svg` using the navbar's teal 5G signal tower icon.
- Updated `index.html` from `.ico` to `.svg` favicon reference.

---

## Phase 1 — Data & ML Model Pipeline

> **Status: ✅ Complete**

### 1a. Raw Data Collection

- **138 CSV files** in `backend/data/` from 5G drive-tests on garbage trucks (garbo01–garbo11) over 4 days (4–7 July 2022).
- Each CSV contains: timestamp, GPS coordinates (latitude, longitude), speed, truck ID, server metrics (svr1–svr4), iperf3 results (transfer size, bitrate, retransmissions, congestion window), and square_id.
- Known data quality issues:
  - Invalid coordinates: `latitude=99`, `longitude=999` (GPS signal lost).
  - Timeout values: `svr1–svr4 = 1000` (connection timeout).
  - Missing iperf3 results in many rows.

### 1b. Data Preprocessing — `1_data_preprocessing.ipynb`

- Loaded and concatenated all 138 raw CSV files.
- Cleaned invalid GPS coordinates (filtered rows where `latitude=99` or `longitude=999`).
- Cleaned timeout values (filtered rows where server metrics = 1000).
- Handled missing values and type conversions.
- Performed exploratory data analysis (EDA) on signal quality metrics.
- Produced a cleaned dataset ready for model training.

### 1c. Clustering Model — `2_model_clustering.ipynb`

- **Algorithm:** KMeans clustering (k=3) from scikit-learn.
- **Features:** Geographic coordinates + signal quality indicators.
- **Output labels:**
  - Cluster 0 → Yếu (Poor signal quality)
  - Cluster 1 → Trung bình (Medium signal quality)
  - Cluster 2 → Tốt (Good signal quality)
- **Artifacts saved:**
  - `backend/models/clustering_model.pkl` — Trained KMeans model.
  - `backend/models/clustering_scaler.pkl` — StandardScaler used for feature normalisation.
  - `backend/models/pipeline_config.pkl` — Pipeline configuration.
  - `backend/data/map_data.csv` — Output CSV with columns `lat`, `lng`, `cluster` (used by the `/api/map-data` endpoint).

### 1d. Forecasting Model — `3_model_forecasting.ipynb`

- **Algorithm:** XGBoost regression with Optuna hyperparameter tuning.
- **Two separate models:**
  - `xgboost_download_mbps.pkl` — Predicts throughput in Mbps.
  - `xgboost_avg_latency.pkl` — Predicts average latency in ms.
- **Alternative model:** `forecasting_model.h5` (deep learning experiment).
- **Time-series approach:** Rolling window of recent data, temporal features (hour, day-of-week).
- **Output:** `backend/metrics/forecast_data.csv` with columns `timestamp`, `predicted_throughput`, `predicted_latency`.
  - Contains hourly predictions starting from 2022-07-22 04:00.
  - Throughput values: ~27–31 Mbps range.
  - Latency values: ~75–77 ms range.

---

## Backend API Development

> **Status: ✅ Complete**

### Backend Entry Point

- `backend/main.py` (1 line): `from app.main import app` — re-exports the FastAPI app for Uvicorn.
- `backend/app/main.py` (150 lines): All routes, data helpers, and middleware.

### Middleware & Configuration

- **CORS:** Configured with specific allowed origins:
  - `http://localhost:5173` (Vite dev server)
  - `http://localhost:8080` (Docker nginx)
  - `http://localhost:4173` (Vite preview)
- **Environment:** `python-dotenv` loads `backend/.env` at startup for `RESEND_API_KEY` and `CONTACT_TO_EMAIL`.

### API Endpoints

#### `GET /` — Health Check
```json
{ "message": "5G Network Quality API is running." }
```

#### `GET /api/map-data` — Cluster Map Data
- Reads `backend/data/map_data.csv`.
- Validates required columns: `lat`, `lng`, `cluster`.
- Coerces types, drops NaN rows.
- Returns: `[{ "lat": -37.725, "lng": 144.750, "cluster": 1 }, ...]`

#### `GET /api/forecast-data` — Forecast Time Series
- Reads `backend/metrics/forecast_data.csv`.
- Validates required columns: `timestamp`, `predicted_throughput`, `predicted_latency`.
- Parses timestamps, rounds numeric values to 2 decimal places.
- Sorts by timestamp, formats as `YYYY-MM-DD HH:MM`.
- Returns: `[{ "timestamp": "2022-07-22 04:00", "predicted_throughput": 30.85, "predicted_latency": 77.24 }, ...]`

#### `POST /api/contact` — Send Feedback Email
- Request body: `{ "name": str, "email": EmailStr, "message": str }` (Pydantic validated).
- Sends email via Resend API with:
  - From: `5G Dashboard <onboarding@resend.dev>`
  - To: configured `CONTACT_TO_EMAIL`.
  - Reply-To: submitter's email.
  - Subject: `[5G Dashboard] Feedback from {name}`.
  - HTML body with formatted content.
- Error handling: Returns 502 with Resend error details on failure.
- Returns: `{ "status": "sent" }` on success.

---

## Authentication & Admin Panel

> **Status: ✅ Complete**

### Supabase Client — `frontend/src/services/supabase.ts` (6 lines)

- Creates a Supabase client using `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` environment variables.
- Shared singleton used by `LoginView`, `AdminView`, and the router auth guard.

### LoginView.vue (114 lines)

- Centred card layout on a neutral background.
- Email + password form fields with `autocomplete` attributes.
- Calls `supabase.auth.signInWithPassword()`.
- Loading spinner during authentication.
- Red error banner showing Supabase error messages on failure.
- Redirects to `/admin` on successful sign-in.

### AdminView.vue (226 lines)

- **Sticky header** showing authenticated user's email + "Sign Out" button.
- **Section 1 — Data Upload:**
  - File input accepting `.csv` files only.
  - "Upload to S3 Pipeline" button with loading state.
  - Mock upload simulation (1.5s delay) — ready for real S3 integration.
  - Status banner (success/error) after upload.
- **Section 2 — Artifact & Data Viewer:**
  - Two-column grid:
    - **Cleaned Datasets (S3):** Table with filename, date, size (3 mock rows).
    - **Model Registry (S3 Artifacts):** Table with version badge, filename, date, accuracy (3 mock rows).

### Vue Router Auth Guard — `frontend/src/router/index.ts` (54 lines)

7 routes with lazy-loaded components:

| Route | View | Protected? |
|---|---|---|
| `/` | DashboardView | No |
| `/about` | AboutView | No |
| `/architecture` | ArchitectureView | No |
| `/contact` | ContactView | No |
| `/login` | LoginView | No |
| `/admin` | AdminView | **Yes** (`requiresAuth` meta) |
| `/:pathMatch(.*)*` | NotFoundView | No |

**Guard logic:** `router.beforeEach()` checks `supabase.auth.getSession()`. If no active session exists on a route with `meta.requiresAuth`, the user is redirected to `/login`.

---

## Resend Email Integration — Contact Form

> **Status: ✅ Complete**

### Implementation

- Added `POST /api/contact` endpoint to `backend/app/main.py`.
- `ContactRequest` Pydantic model with `name: str`, `email: EmailStr`, `message: str`.
- Resend API configured via `RESEND_API_KEY` environment variable.
- Email sent to `CONTACT_TO_EMAIL` (configured in `backend/.env`).

### Dependencies Added

- `resend` — Transactional email API client.
- `email-validator` — Email address validation for Pydantic `EmailStr`.
- `python-dotenv` — `.env` file loading.

### Frontend Integration

- `ContactView.vue` calls `axios.post()` to the backend endpoint.
- Client-side validation (name, email format, message required).
- Loading state (`submitting` ref) disables the submit button.
- Error banner shows API error details or a generic fallback message.
- Success state shows green confirmation card.

### Bug Fix — 500 Internal Server Error

Three compounding issues were identified and resolved:

1. **Missing `load_dotenv()` call:** `python-dotenv` was installed but not invoked at startup → `RESEND_API_KEY` was empty.
   - **Fix:** Added `load_dotenv(Path(__file__).resolve().parents[1] / ".env")` at the top of `main.py`.

2. **Wrong recipient email:** Resend free tier only allows sending to the account owner's email. `CONTACT_TO_EMAIL` was set to the wrong address.
   - **Fix:** Changed to the correct Resend-verified email in `backend/.env`.

3. **Missing error handling:** `resend.Emails.send()` had no try/except, so `ResendError` became a generic 500.
   - **Fix:** Wrapped in `try/except resend.exceptions.ResendError` → returns `HTTPException(502)` with details.

---

## Cloud Architecture Design

> **Status: ✅ Designed & Documented (not yet deployed)**

### Finalized Architecture (AWS + Supabase)

Documented in `.github/copilot-instructions.md` and visualised in the ArchitectureView.

**Authentication layer:**
- Developers access a hidden `/admin` route.
- **Supabase** handles email/password authentication and issues JWTs.
- FastAPI verifies Supabase JWTs before serving protected endpoints.

**Serving layer:**
- **AWS CloudFront** serves the Vue 3 frontend as a static site (CDN).
- **AWS API Gateway + AWS Lambda (via Mangum)** hosts the FastAPI backend as a serverless function.

**MLOps Pipeline (Continuous Training) — 6 steps:**

1. **Developer Upload** → Authenticated admin uploads new 5G CSV to **S3 Raw Data** bucket.
2. **Lambda Trigger** → S3 event notification triggers a single **AWS Lambda** function.
3. **SageMaker Pipeline: Process** → Processing job cleans invalid coordinates (99999) and timeouts (1000), merges with historical **Feature Store** in S3.
4. **SageMaker Pipeline: Train** → Training job runs KMeans clustering + XGBoost time-series forecasting using a rolling window.
5. **Model Evaluation** → Compares new Challenger model vs current Champion using silhouette scores and RMSE.
6. **Model Registry** → Approved `.pkl` artifacts are versioned and stored in **S3 Artifacts** bucket.

**Inference Flow (Live Dashboard) — 5 steps:**

1. **Dashboard Access** → User accesses the 5G Dashboard via **CloudFront CDN**.
2. **Supabase Auth** → Admin users authenticate; Supabase issues JWT.
3. **API Gateway & Lambda** → Vue app calls `/api`. CloudFront routes API requests to **API Gateway**, which triggers the **Lambda container** (Mangum wrapper) running FastAPI to verify tokens and handle the request.
4. **S3 Artifacts** → FastAPI (inside Lambda) loads the latest approved model artifacts into memory.
5. **Live Predictions** → Backend runs inference, returning GeoJSON and forecast arrays.

### Interactive Architecture Components

#### AWSArchitectureMap.vue (240 lines)

Two-column parallel timeline component:

- **Column 1 — MLOps Training Flow:** 6 step cards with vertical connectors.
- **Column 2 — User Inference Flow:** 5 step cards with vertical connectors.
- **Simulation buttons:** "Simulate MLOps Pipeline" (violet) and "Simulate User Request" (sky blue).
- **Animations:**
  - Active step: `ring-4 ring-orange-500 ring-offset-2` glow + pulsing "Active" badge.
  - Completed steps: emerald background with check-mark icon.
  - Connector lines transition from grey to emerald.
  - Buttons disabled during simulation.
  - 1.3s delay between each step, 1.8s hold on the final step.

#### MLOpsPipeline.vue (276 lines)

Vertical timeline with richer visual detail:

- 6 pipeline nodes with unique accent colours (sky, indigo, violet, amber, emerald, teal).
- Each node: icon badge, title, sublabel, detailed description.
- **Progress bar** at the top showing pipeline completion percentage.
- **Simulation controls:** "Simulate New Data Upload" button + "Reset" button.
- 1.5s step interval, 2s final hold.
- Icon badges animate between states (grey → coloured → emerald check).

---

## Docker & DevOps

> **Status: ✅ Basic setup complete; hardening planned for Phase 3**

### docker-compose.yml

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    ports:
      - "8080:80"
    depends_on:
      - backend
```

### Backend Dockerfile

- Base: `python:3.10-slim`
- Installs dependencies from `requirements.txt` (32 packages).
- Copies application code.
- Exposes port 8000.
- CMD: `uvicorn main:app --host 0.0.0.0 --port 8000`

### Frontend Dockerfile

- **Build stage:** `node:20-alpine` — installs npm packages, runs `npm run build`.
- **Production stage:** `nginx:stable-alpine` — copies built `dist/` to nginx HTML root.
- Exposes port 80.

### Access URLs

| Service | URL |
|---|---|
| Frontend Dashboard | `http://localhost:8080` |
| Backend API | `http://localhost:8000` |
| Swagger Docs | `http://localhost:8000/docs` |
| Vite Dev Server (local) | `http://localhost:5173` |

---

## Bug Fixes & Debugging Log

### Bug 1: ArchitectureView.vue — `require()` fails in Vite

- **Problem:** Used `require()` CommonJS import for `AWSArchitecture.png`, which is not supported by Vite (ESM only).
- **Fix:** Replaced with ES import: `import architectureImage from '../assets/AWSArchitecture.png'`.

### Bug 2: DashboardView.vue — TypeScript strict-mode error

- **Problem:** Docker build failed with `TS18048: 'cfg' is possibly 'undefined'` on cluster config lookup.
- **Root cause:** `Record<number, T>` index signature returns `T | undefined` under strict mode.
- **Fix:** Added non-null assertion with fallback: `const cfg = (clusterConfig[point.cluster] ?? clusterConfig[1])!`

### Bug 3: Contact form — 500 Internal Server Error

- **Problem:** `POST /api/contact` returned HTTP 500 with no useful error message.
- **Root cause:** Three compounding issues — missing `load_dotenv()`, wrong recipient email for Resend free tier, and no error handling on `resend.Emails.send()`.
- **Fix:** Added env loading, corrected email, wrapped in try/except with proper HTTP 502 response.

### Bug 4: CORS configuration tightened

- **Problem:** Original backend used `allow_origins=["*"]` (wildcard).
- **Fix:** Updated to specific allowed origins list: `localhost:5173`, `localhost:8080`, `localhost:4173`.

---

## Current Project Status

### Completed Phases

| Phase | Description | Status |
|---|---|---|
| **Phase 0** | Frontend UI/UX Foundation | ✅ Complete |
| **Phase 1** | Data & ML Model Pipeline | ✅ Complete |
| **Backend API** | FastAPI endpoints + data helpers | ✅ Complete |
| **Authentication** | Supabase login + admin panel | ✅ Complete |
| **Contact Form** | Resend email integration | ✅ Complete |
| **Architecture** | Cloud architecture design + interactive visualisation | ✅ Complete |
| **Docker** | Docker Compose basic setup | ✅ Complete |

### Remaining Work

| Phase | Description | Status |
|---|---|---|
| **Phase 2** | Backend refactor (routers/services/schemas) | 🔲 Not started |
| **Phase 3** | Docker hardening (healthchecks, pinned versions, nginx proxy) | 🔲 Not started |
| **Phase 4** | Testing (pytest backend, Cypress E2E frontend) | 🔲 Not started |
| **Cloud Deploy** | AWS infrastructure provisioning + deployment | 🔲 Not started |

### Model Artifacts Produced

| Artifact | File | Description |
|---|---|---|
| KMeans Clustering | `clustering_model.pkl` | 3-cluster signal quality classifier |
| Feature Scaler | `clustering_scaler.pkl` | StandardScaler for clustering input |
| Pipeline Config | `pipeline_config.pkl` | Model pipeline configuration |
| Throughput Forecaster | `xgboost_download_mbps.pkl` | XGBoost regression for Mbps prediction |
| Latency Forecaster | `xgboost_avg_latency.pkl` | XGBoost regression for latency prediction |
| Deep Learning Model | `forecasting_model.h5` | Alternative neural network experiment |

### Data Outputs

| Output | File | Description |
|---|---|---|
| Map cluster data | `backend/data/map_data.csv` | Lat/lng/cluster for every cleaned measurement point |
| Forecast series | `backend/metrics/forecast_data.csv` | Hourly throughput + latency predictions |

---

## Complete File Inventory

### Files Created

| # | File | Lines | Description |
|---|---|---|---|
| 1 | `frontend/src/components/AWSArchitectureMap.vue` | 240 | Interactive cloud infra explorer |
| 2 | `frontend/src/components/MLOpsPipeline.vue` | 276 | Animated MLOps pipeline timeline |
| 3 | `frontend/src/components/FooterComp.vue` | 77 | Global footer component |
| 4 | `frontend/src/views/DashboardView.vue` | 283 | Main dashboard: map + chart |
| 5 | `frontend/src/views/AboutView.vue` | 192 | Team member page |
| 6 | `frontend/src/views/ArchitectureView.vue` | 229 | Architecture documentation page |
| 7 | `frontend/src/views/ContactView.vue` | 245 | Contact form + links |
| 8 | `frontend/src/views/AdminView.vue` | 226 | Protected admin panel |
| 9 | `frontend/src/views/LoginView.vue` | 114 | Supabase sign-in page |
| 10 | `frontend/src/views/NotFoundView.vue` | 26 | 404 page |
| 11 | `frontend/src/services/supabase.ts` | 6 | Supabase client singleton |
| 12 | `frontend/src/services/mockData.ts` | 99 | Type definitions + seeded mock data |
| 13 | `frontend/public/favicon.svg` | 3 | Custom SVG favicon |

### Files Modified

| # | File | Lines | Changes |
|---|---|---|---|
| 1 | `frontend/src/App.vue` | 93 | Navbar with router links + mobile menu |
| 2 | `frontend/src/router/index.ts` | 54 | 7 routes + Supabase auth guard |
| 3 | `frontend/src/assets/main.css` | 34 | Tailwind v4 entry + @theme tokens |
| 4 | `frontend/index.html` | 18 | Inter font, SVG favicon, meta description |
| 5 | `frontend/vite.config.ts` | 20 | @tailwindcss/vite plugin |
| 6 | `frontend/package.json` | — | Added dependencies (supabase, axios, echarts, leaflet) |
| 7 | `backend/app/main.py` | 150 | All API routes + data helpers + email endpoint |
| 8 | `backend/requirements.txt` | 32 | Full dependency list |
| 9 | `backend/.env` | 2 | Resend API key + contact email |
| 10 | `.github/copilot-instructions.md` | 178 | Project rules + cloud architecture docs |
| 11 | `docker-compose.yml` | 12 | Backend + frontend service definitions |
| 12 | `README.md` | 44 | Quick-start guide |

### ML Notebooks

| # | File | Description |
|---|---|---|
| 1 | `backend/1_data_preprocessing.ipynb` | Data cleaning, EDA, feature engineering |
| 2 | `backend/2_model_clustering.ipynb` | KMeans training, evaluation, artifact export |
| 3 | `backend/3_model_forecasting.ipynb` | XGBoost forecasting, Optuna tuning, artifact export |

### Model & Data Artifacts

| # | File | Type |
|---|---|---|
| 1 | `backend/models/clustering_model.pkl` | Trained KMeans model |
| 2 | `backend/models/clustering_scaler.pkl` | StandardScaler |
| 3 | `backend/models/pipeline_config.pkl` | Pipeline config |
| 4 | `backend/models/xgboost_download_mbps.pkl` | XGBoost throughput model |
| 5 | `backend/models/xgboost_avg_latency.pkl` | XGBoost latency model |
| 6 | `backend/models/forecasting_model.h5` | Deep learning model |
| 7 | `backend/data/map_data.csv` | Clustering output |
| 8 | `backend/metrics/forecast_data.csv` | Forecasting output |
| 9 | `backend/data/*.csv` (138 files) | Raw 5G telemetry data |
