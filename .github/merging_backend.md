# Integration Audit Report — Frontend ↔ Backend Merge

**Date:** 2026-03-23  
**Engineer:** Lead Integration (GitHub Copilot)  
**Scope:** `frontend/src/views/DashboardView.vue` + `frontend/src/services/mockData.ts` vs `backend/app/main.py`

---

## Executive Summary

| Area | Status | Severity |
|---|---|---|
| Map data schema | ❌ MISMATCH — structure + 3 key names | **CRITICAL** |
| Forecast data schema | ❌ MISMATCH — shape + 2 key names + 1 missing field | **CRITICAL** |
| CORS configuration | ✅ Wildcard origin — works for dev | LOW |
| Vite dev proxy | ⚠️ Not configured | MEDIUM |
| Docker networking | ⚠️ No named network, no nginx proxy for `/api/` | MEDIUM |

---

## 1. Data Schema Verification

### 1a. Map Endpoint — `GET /api/map-data`

#### What the backend returns

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [100.5018, 13.7563]
      },
      "properties": {
        "square_id": "SQ-001",
        "quality": "Tot"
      }
    }
  ]
}
```

Key details:
- **Shape**: GeoJSON `FeatureCollection`, not a flat array.
- **Coordinates**: GeoJSON order is `[longitude, latitude]` — i.e., `coordinates[0]` = lng, `coordinates[1]` = lat.
- **Quality labels**: String values — `"Tot"` | `"Trung binh"` | `"Yeu"`.
- **No cluster number**: There is no integer `cluster` field anywhere.

#### What the frontend currently expects (`ClusterPoint` type)

```typescript
// mockData.ts
export type ClusterPoint = {
  lat: number       // → backend: feature.geometry.coordinates[1]
  lng: number       // → backend: feature.geometry.coordinates[0]
  cluster: 0 | 1 | 2  // → backend: DOES NOT EXIST — derived from quality string
}

// renderMap() accesses:
point.lat
point.lng
point.cluster   // used as key into clusterConfig{}
```

#### Mismatches — Map

| Frontend key | Backend equivalent | Action required on frontend |
|---|---|---|
| `point.lat` | `feature.geometry.coordinates[1]` | Extract from coordinates array |
| `point.lng` | `feature.geometry.coordinates[0]` | Extract from coordinates array |
| `point.cluster` (0/1/2) | `feature.properties.quality` ("Tot"/"Trung binh"/"Yeu") | Replace `clusterConfig` integer keys with string keys |
| _(entire flat array shape)_ | Nested `FeatureCollection` structure | Parse `response.features` array |

**Fix strategy for `renderMap`:** Update the function signature to accept `feature` objects directly from the GeoJSON response, or write a mapper that converts `features[]` → `ClusterPoint[]`. The `clusterConfig` record must change its key type from `number` to `string`:

```typescript
// REPLACE THIS:
const clusterConfig: Record<number, ...> = {
  0: { label: 'Yếu', ... },
  1: { label: 'Trung bình', ... },
  2: { label: 'Tốt', ... },
}

// WITH THIS:
const clusterConfig: Record<string, { label: string; color: string; sublabel: string }> = {
  'Yeu':       { label: 'Yếu',        color: '#dc2626', sublabel: 'Poor'   },
  'Trung binh':{ label: 'Trung bình', color: '#f59e0b', sublabel: 'Medium' },
  'Tot':       { label: 'Tốt',        color: '#17a34a', sublabel: 'Good'   },
}
```

And `renderMap` must draw from `feature.geometry.coordinates` rather than `point.lat`/`point.lng`.

---

### 1b. Forecast Endpoint — `GET /api/forecast-data`

#### What the backend returns

```json
{
  "time": ["2026-03-13 08:00:00", "2026-03-13 09:00:00", "..."],
  "predicted_speed_mbps": [142.0, 146.5, 151.2, "..."]
}
```

Key details:
- **Shape**: Object with two **parallel arrays** (not an array of objects).
- **No latency data**: The backend has no latency column. The `renderChart` dual-axis (Latency line) will be empty/broken.

#### What the frontend currently expects (`ForecastPoint` type)

```typescript
// mockData.ts
export type ForecastPoint = {
  timestamp: string         // → backend: "time" array
  predicted_throughput: number  // → backend: "predicted_speed_mbps" array
  predicted_latency: number     // → backend: NOT PRESENT
}

// renderChart() accesses:
p.timestamp
p.predicted_throughput
p.predicted_latency   // ← will be undefined for every point
```

#### Mismatches — Forecast

| Frontend field | Backend key | Action required |
|---|---|---|
| `ForecastPoint[].timestamp` | `response.time[]` | Rename key when mapping |
| `ForecastPoint[].predicted_throughput` | `response.predicted_speed_mbps[]` | Rename key when mapping |
| `ForecastPoint[].predicted_latency` | **MISSING** | Either: (A) add a `predicted_latency_ms` array to the backend, or (B) remove the Latency series from the chart |

**Fix strategy for `renderChart`:** Zip `response.time` and `response.predicted_speed_mbps` into the existing `ForecastPoint` shape on the frontend side:

```typescript
// Adapter to call after axios.get('/api/forecast-data')
function adaptForecast(raw: { time: string[]; predicted_speed_mbps: number[] }): ForecastPoint[] {
  return raw.time.map((t, i) => ({
    timestamp: t,
    predicted_throughput: raw.predicted_speed_mbps[i] ?? 0,
    predicted_latency: 0,   // placeholder until backend adds this field
  }))
}
```

---

## 2. CORS Configuration

**Finding:** `allow_origins=["*"]` is set in `backend/app/main.py`.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # ← wildcard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Impact:** The Vite dev server at `http://localhost:5173` will **not** be blocked by CORS. ✅ No action needed for local development.

> ⚠️ **Post-integration hardening note (Phase 3):** `allow_credentials=True` combined with `allow_origins=["*"]` is technically rejected by the browser spec — Firefox/Chrome will silently ignore the wildcard and block credentialed requests. Since no cookies or `Authorization` headers are currently sent, this is not a current blocker, but replace `"*"` with explicit origins before any production deployment:
> ```python
> allow_origins=["http://localhost:5173", "http://localhost:8080"]
> ```

---

## 3. API Routing — Vite Dev Proxy

**Finding:** `vite.config.ts` has **no `server.proxy` configuration**. Without it, an Axios call to `/api/map-data` from the dev server (`http://localhost:5173`) targets `http://localhost:5173/api/map-data` — a 404 — instead of `http://localhost:8000/api/map-data`.

#### Exact code block to add to `vite.config.ts`

```typescript
// vite.config.ts  — add the `server` block shown below
export default defineConfig({
  plugins: [
    tailwindcss(),
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

No path rewriting is needed because both sides already use the `/api/` prefix.

---

## 4. Docker Readiness

### 4a. Network

**Finding:** `docker-compose.yml` declares no explicit named network.

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

Docker Compose automatically creates a default bridge network for the project and attaches all services to it. The backend is therefore reachable from inside the frontend container as `http://backend:8000`. This is **sufficient** — no action is strictly required — but adding an explicit network is best practice for clarity.

### 4b. The Vite proxy does NOT survive containerisation ⚠️

The `server.proxy` added in §3 is a **Vite dev-server feature only**. In Docker, the frontend is built with `vite build` and then served by **nginx** — the Vite process never runs. This means:

- In Docker, if `DashboardView.vue` calls `axios.get('/api/map-data')`, the request goes to nginx on port 80, which will return a 404 unless nginx is configured to forward `/api/` requests.
- The current `frontend/Dockerfile` (multi-stage: `node:20 build → nginx:stable-alpine`) does **not** include nginx proxy rules.

#### Two valid solutions (choose one before Phase 3)

**Option A — nginx reverse proxy (recommended, no CORS involved)**  
Add a `location /api/` block to the nginx config so that requests to `http://localhost:8080/api/...` are proxied to `http://backend:8000/api/...` internally:

```nginx
# frontend/nginx.conf  (to be created and COPYed in the Dockerfile)
server {
    listen 80;
    location / {
        root   /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
    location /api/ {
        proxy_pass         http://backend:8000;
        proxy_set_header   Host $host;
    }
}
```

**Option B — `VITE_API_BASE_URL` build-arg**  
Inject the backend's public URL at build time so Axios uses the full URL directly:

```typescript
// In DashboardView.vue (axios call)
const BASE = import.meta.env.VITE_API_BASE_URL ?? ''
await axios.get(`${BASE}/api/map-data`)
```

```yaml
# docker-compose.yml
frontend:
  build:
    context: ./frontend
    args:
      - VITE_API_BASE_URL=http://localhost:8000
```

Option A is preferred (matches the project architecture guidelines in `.github/copilot-instructions.md`, Phase 3).

### 4c. Healthcheck gap ⚠️

`depends_on: backend` does **not** wait for the FastAPI server to be ready — it only waits for the container to start. If `uvicorn` takes a few seconds to boot, the frontend container might attempt its first request before the API is available.

Recommended addition (Phase 3):
```yaml
backend:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/"]
    interval: 10s
    retries: 5
frontend:
  depends_on:
    backend:
      condition: service_healthy
```

---

## Action Checklist Before Integration Testing

| # | Action | File | Owner |
|---|---|---|---|
| 1 | Change `clusterConfig` keys from integers to quality strings (`"Tot"`, `"Trung binh"`, `"Yeu"`) | `DashboardView.vue` | Frontend |
| 2 | Update `renderMap` to parse GeoJSON `FeatureCollection` structure (coordinates array, properties.quality) | `DashboardView.vue` | Frontend |
| 3 | Update `renderChart` to accept `{time, predicted_speed_mbps}` parallel-array shape | `DashboardView.vue` | Frontend |
| 4 | Drop or stub `predicted_latency` on the chart until the backend adds the field | `DashboardView.vue` | Frontend |
| 5 | Add `server.proxy` block to `vite.config.ts` | `vite.config.ts` | Frontend |
| 6 | Switch `DashboardView.vue` from mock data to `axios` calls | `DashboardView.vue` | Frontend |
| 7 | *(Recommended — Phase 3)* Add `nginx.conf` with `/api/` proxy_pass for Docker | `frontend/nginx.conf` | DevOps |
| 8 | *(Recommended — Phase 3)* Add backend healthcheck + `condition: service_healthy` to Compose | `docker-compose.yml` | DevOps |
| 9 | *(Recommended — Phase 3)* Add `predicted_latency_ms` column to forecast endpoint | `backend/app/main.py` | Backend |
