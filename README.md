# 5G Network Quality Dashboard

A full-stack AI engineering dashboard (COS40007) that visualises 5G network coverage quality on an interactive map and forecasts throughput / latency over time. The ML pipeline includes K-Means/GMM clustering and a four-model forecasting benchmark (XGBoost, CatBoost, Bidirectional LSTM, 1D CNN). The system is deployed on AWS using a fully serverless architecture.

**Live:** <https://d33m3uevv39v9p.cloudfront.net>

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Frontend | Vue 3 (Composition API, `<script setup>`) | 3.5.29 |
| Build | Vite | 7.3.1 |
| CSS | Tailwind CSS v4 (`@tailwindcss/vite` plugin) | 4.2.2 |
| Map | Leaflet + GeoJSON | 1.9.4 |
| Chart | Apache ECharts | 6.0.0 |
| HTTP client | Axios | 1.13.2 |
| Auth | Supabase (supabase-js) | 2.100.1 |
| State | Pinia | 3.0.4 |
| Routing | Vue Router (history mode) | 5.0.3 |
| Backend | FastAPI + Uvicorn (local) / Mangum (Lambda) | latest |
| ML / data | scikit-learn, pandas, numpy, XGBoost, CatBoost, TensorFlow/Keras | latest |
| Containerisation | Docker Compose v2 | — |
| Cloud | AWS (CloudFront, API Gateway, Lambda, S3, SageMaker, ECR) | — |

---

## Repository Structure

```
AI4Eng_Theme5/
├── README.md
├── Final Report.md
├── docker-compose.yml
├── aws/
│   ├── AWS_Deployment_Plan.md
│   ├── backend_ECR/              ← Lambda Docker build context
│   ├── frontend_Deployment/      ← S3 + CloudFront deploy scripts
│   ├── lambda_trigger/           ← S3→SageMaker trigger Lambda
│   ├── lambda_policy/            ← IAM policy JSONs
│   └── sagemaker/
│       ├── pipeline_definition.py
│       └── scripts/              ← preprocess.py, train_clustering.py, train_forecasting.py
├── backend/
│   ├── Dockerfile                ← Docker Compose (uvicorn)
│   ├── Dockerfile.lambda         ← Lambda container image (Mangum)
│   ├── requirements.txt
│   ├── requirements.lambda.txt   ← slim deps for Lambda (no training libs)
│   ├── main.py                   ← re-exports: from app.main import app
│   ├── app/
│   │   └── main.py               ← FastAPI routes + S3 helpers + Mangum handler
│   ├── 1_data_preprocessing.ipynb
│   ├── 2_model_clustering.ipynb
│   ├── 3_model_forecasting.ipynb
│   ├── notebooks/                ← archived notebook versions
│   ├── data/                     ← raw 5G CSVs + map_data.csv
│   ├── metrics/                  ← forecast_data.csv
│   └── models/                   ← trained .pkl / .h5 artifacts
└── frontend/
    ├── Dockerfile                ← multi-stage: node build → nginx
    ├── index.html
    ├── vite.config.ts
    └── src/
        ├── main.ts
        ├── assets/main.css       ← Tailwind entry (@import "tailwindcss")
        ├── router/index.ts
        ├── services/             ← Supabase client
        ├── stores/               ← Pinia stores
        └── views/
            ├── DashboardView.vue
            ├── AboutView.vue
            ├── ArchitectureView.vue
            ├── ContactView.vue
            ├── LoginView.vue
            ├── AdminView.vue
            └── NotFoundView.vue
```

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

| Service | Local Dev | Docker Compose | Production |
|---|---|---|---|
| Frontend Dashboard | `http://localhost:5173` | `http://localhost:8080` | `https://d33m3uevv39v9p.cloudfront.net` |
| Backend API | `http://localhost:8000` | `http://localhost:8000` | via CloudFront `/api/*` proxy |
| Swagger Docs | `http://localhost:8000/docs` | `http://localhost:8000/docs` | — |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/api/map-data` | Cluster map data (`lat`, `lng`, `cluster`) |
| `GET` | `/api/forecast-data` | Forecast series (`timestamp`, `predicted_throughput`, `predicted_latency`) |
| `POST` | `/api/contact` | Send feedback email via Resend |
| `GET` | `/api/raw-data` | List raw CSV files in S3 |
| `GET` | `/api/cleaned-data` | List cleaned data files in S3 |
| `GET` | `/api/models` | List model artifacts in S3 |

---

## Frontend Pages

| Route | View | Description |
|---|---|---|
| `/` | DashboardView | Interactive Leaflet map + ECharts dual-axis forecast chart |
| `/about` | AboutView | Team member cards with scroll-reveal animations |
| `/architecture` | ArchitectureView | MLOps pipeline diagram, AWS infra, tech stack, roadmap |
| `/contact` | ContactView | Contact form (Resend email API) |
| `/login` | LoginView | Supabase email/password authentication |
| `/admin` | AdminView | Protected — CSV upload, S3 raw/cleaned/model viewers |
| `/*` | NotFoundView | Custom 404 page |

---

## ML Pipeline

### Notebooks

| Notebook | Purpose |
|---|---|
| `1_data_preprocessing.ipynb` | Load 138 raw CSVs → clean (GPS validation, bounding box, outlier capping) → 1 s resampling → 50+ engineered features → temporal train/test split |
| `2_model_clustering.ipynb` | 5 features → Winsorise P5/P95 → log1p → RobustScaler → PCA → KMeans/GMM (k=3). Silhouette = 0.419. Winner: GMM |
| `3_model_forecasting.ipynb` | 25 tree features, SEQ_LEN=12, 4-model benchmark. Winner: CatBoost (avg R² = 0.919) |

### Model Artifacts (`backend/models/`)

| File | Description |
|---|---|
| `clustering_model.pkl` | GMM clustering model (3 clusters) |
| `clustering_scaler.pkl` | RobustScaler for clustering features |
| `clustering_pca.pkl` | PCA transformer (2 components) |
| `clustering_config.json` | Feature list, cluster labels, thresholds |
| `catboost_download_mbps.pkl` | CatBoost throughput model (winner) |
| `catboost_avg_latency.pkl` | CatBoost latency model (winner) |
| `xgboost_download_mbps.pkl` | XGBoost throughput model |
| `xgboost_avg_latency.pkl` | XGBoost latency model |
| `forecasting_model.h5` | Bidirectional LSTM model |
| `pipeline_config.pkl` | Feature scaler + column config |

---

## AWS Deployment

| Component | Service | Details |
|---|---|---|
| Frontend hosting | S3 + CloudFront | OAC, SPA routing, `/api/*` proxy to backend |
| Backend API | API Gateway + Lambda | ECR container image, Mangum ASGI adapter, 512 MB / 30 s |
| ML retraining | SageMaker Pipelines | 3-step: Preprocess → Clustering + Forecasting (parallel) |
| Pipeline trigger | Lambda (S3 event) | Admin uploads CSV → triggers `5g-quality-pipeline` |
| Auth | Supabase | JWT verification for admin routes |

---

## Data / Model Folders

- `backend/data/` — raw 5G drive-test CSVs + `map_data.csv` (clustering output)
- `backend/metrics/` — `forecast_data.csv` (12-hour forecast output)
- `backend/models/` — trained model artifacts (`.pkl`, `.h5`, `.json`)

If CSV files are missing, the backend returns a `404` with a descriptive error message.
