/**
 * Realistic mock data for the 5G Network Quality Dashboard.
 * Coordinates are centred on Brimbank City Council, Melbourne (~-37.75, 144.82).
 *
 * Cluster labels:
 *   0 → Yếu   (Poor)   — red
 *   1 → Trung bình (Medium) — amber
 *   2 → Tốt   (Good)   — green
 */

export type ClusterPoint = {
  lat: number
  lng: number
  cluster: 0 | 1 | 2
}

export type ForecastPoint = {
  timestamp: string
  predicted_throughput: number  // Mbps
  predicted_latency: number     // ms
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Seeded pseudo-random so the data looks stable across hot-reloads. */
function seededRandom(seed: number): () => number {
  let s = seed
  return () => {
    s = (s * 16807 + 0) % 2147483647
    return (s - 1) / 2147483646
  }
}

const rng = seededRandom(42)

/** Return a float in [min, max] using the seeded RNG. */
function rand(min: number, max: number): number {
  return min + rng() * (max - min)
}

/** Round to n decimal places. */
function round(v: number, n = 5): number {
  return Math.round(v * 10 ** n) / 10 ** n
}

// ---------------------------------------------------------------------------
// mockMapData — 57 cluster points around Brimbank, Melbourne
// ---------------------------------------------------------------------------

// Brimbank suburbs bbox: lat -37.69 .. -37.82, lng 144.77 .. 144.92
const BRIMBANK_BOUNDS = { latMin: -37.82, latMax: -37.69, lngMin: 144.77, lngMax: 144.92 }

// Weighted distribution: 50% Good, 30% Medium, 20% Poor (realistic 5G urban scenario)
const CLUSTER_WEIGHTS: Array<0 | 1 | 2> = [
  2, 2, 2, 2, 2,  // 5× Tốt
  1, 1, 1,        // 3× Trung bình
  0, 0,           // 2× Yếu
]

function pickCluster(): 0 | 1 | 2 {
  return CLUSTER_WEIGHTS[Math.floor(rng() * CLUSTER_WEIGHTS.length)] ?? 2
}

export const mockMapData: ClusterPoint[] = Array.from({ length: 57 }, () => ({
  lat: round(rand(BRIMBANK_BOUNDS.latMin, BRIMBANK_BOUNDS.latMax)),
  lng: round(rand(BRIMBANK_BOUNDS.lngMin, BRIMBANK_BOUNDS.lngMax)),
  cluster: pickCluster(),
}))

// ---------------------------------------------------------------------------
// mockForecastData — next 12 hours of predicted network performance
// ---------------------------------------------------------------------------

// Baseline values that drift hour-by-hour to simulate realistic fluctuation
const BASE_THROUGHPUT = 145   // Mbps
const BASE_LATENCY    = 18    // ms

// Small random walk offsets so each run of the series feels organic
const THROUGHPUT_OFFSETS = [0, 4.2, 8.7, 6.1, 11.3, 15.8, 13.4, 18.1, 22.6, 20.9, 25.3, 19.7]
const LATENCY_OFFSETS    = [0, -0.5, 1.2, -0.8, 1.5, 2.1, -1.0, 1.8, -0.3, 2.4, 1.1, -0.6]

function buildTimestamp(hoursFromNow: number): string {
  const d = new Date()
  d.setMinutes(0, 0, 0)
  d.setHours(d.getHours() + hoursFromNow)
  return d.toISOString().replace('T', ' ').slice(0, 16)  // "YYYY-MM-DD HH:MM"
}

export const mockForecastData: ForecastPoint[] = Array.from({ length: 12 }, (_, i) => {
  const noise = rand(-3, 3)
  const latNoise = rand(-1.5, 1.5)
  return {
    timestamp: buildTimestamp(i),
    predicted_throughput: Math.round((BASE_THROUGHPUT + (THROUGHPUT_OFFSETS[i] ?? 0) + noise) * 10) / 10,
    predicted_latency: Math.round((BASE_LATENCY + (LATENCY_OFFSETS[i] ?? 0) + latNoise) * 10) / 10,
  }
})
