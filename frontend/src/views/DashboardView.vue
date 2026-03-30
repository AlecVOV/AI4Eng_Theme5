<script setup lang="ts">
import axios from 'axios'
import * as echarts from 'echarts'
import L from 'leaflet'
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import type { ClusterPoint, ForecastPoint } from '../services/mockData'

const API = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const mapContainerRef = ref<HTMLDivElement | null>(null)
const chartContainerRef = ref<HTMLDivElement | null>(null)
const loading = ref(true)
const isMapLoading = ref(false)
const isChartLoading = ref(false)
const errorMessage = ref('')

let map: L.Map | null = null
let chart: echarts.ECharts | null = null

const clusterConfig: Record<number, { label: string; color: string; sublabel: string }> = {
  0: { label: 'Yếu',        color: '#dc2626', sublabel: 'Poor'   },
  1: { label: 'Trung bình', color: '#f59e0b', sublabel: 'Medium' },
  2: { label: 'Tốt',        color: '#17a34a', sublabel: 'Good'   },
}

const qualityLegend = Object.values(clusterConfig)

async function loadDashboardData(): Promise<void> {
  loading.value = true
  isMapLoading.value = true
  isChartLoading.value = true
  errorMessage.value = ''

  try {
    const [mapRes, forecastRes] = await Promise.all([
      axios.get<ClusterPoint[]>(`${API}/api/map-data`),
      axios.get<ForecastPoint[]>(`${API}/api/forecast-data`),
    ])

    loading.value = false
    await nextTick()

    isMapLoading.value = false
    renderMap(mapRes.data)

    isChartLoading.value = false
    renderChart(forecastRes.data)
  } catch (error) {
    loading.value = false
    isMapLoading.value = false
    isChartLoading.value = false

    if (axios.isAxiosError(error)) {
      const status = error.response?.status
      const detail = error.response?.data?.detail
      errorMessage.value = detail
        ? `API error (${status}): ${detail}`
        : `Cannot reach API at ${API} — is the backend running?`
    } else {
      errorMessage.value =
        error instanceof Error
          ? `Không thể tải dữ liệu dashboard: ${error.message}`
          : 'Không thể tải dữ liệu dashboard.'
    }
  }
}

function renderMap(points: ClusterPoint[]): void {
  if (!mapContainerRef.value) return

  if (map) map.remove()

  map = L.map(mapContainerRef.value, { zoomControl: true }).setView([-37.755, 144.845], 13)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(map)

  const markers: L.CircleMarker[] = []

  for (const point of points) {
    const cfg = (clusterConfig[point.cluster] ?? clusterConfig[1])!
    const marker = L.circleMarker([point.lat, point.lng], {
      radius: 8,
      fillColor: cfg.color,
      color: '#ffffff',
      weight: 1.5,
      opacity: 1,
      fillOpacity: 0.85,
    })
    marker.bindPopup(
      `<strong>Cluster ${point.cluster}</strong> — ${cfg.label}<br/>` +
      `<span style="font-size:0.8em;color:#6b7280">` +
      `${point.lat.toFixed(5)}, ${point.lng.toFixed(5)}</span>`,
    )
    marker.addTo(map)
    markers.push(marker)
  }

  if (markers.length > 0) {
    const group = L.featureGroup(markers)
    map.fitBounds(group.getBounds().pad(0.15))
  }
}

function renderChart(points: ForecastPoint[]): void {
  if (!chartContainerRef.value) return

  if (chart) chart.dispose()

  const timestamps = points.map((p) => p.timestamp)
  const throughput  = points.map((p) => p.predicted_throughput)
  const latency     = points.map((p) => p.predicted_latency)

  chart = echarts.init(chartContainerRef.value)
  chart.setOption({
    grid: { left: 56, right: 56, top: 56, bottom: 72 },
    legend: {
      top: 8,
      data: ['Throughput (Mbps)', 'Latency (ms)'],
      textStyle: { fontSize: 12 },
    },
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    xAxis: {
      type: 'category',
      data: timestamps,
      axisLabel: { rotate: 30, fontSize: 11 },
    },
    yAxis: [
      {
        type: 'value',
        name: 'Mbps',
        position: 'left',
        nameTextStyle: { fontSize: 11 },
        axisLabel: { fontSize: 11 },
      },
      {
        type: 'value',
        name: 'ms',
        position: 'right',
        nameTextStyle: { fontSize: 11 },
        axisLabel: { fontSize: 11 },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: 'Throughput (Mbps)',
        type: 'line',
        yAxisIndex: 0,
        smooth: true,
        data: throughput,
        lineStyle: { width: 3, color: '#0f766e' },
        itemStyle: { color: '#0f766e' },
        areaStyle: { color: 'rgba(15, 118, 110, 0.10)' },
      },
      {
        name: 'Latency (ms)',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        data: latency,
        lineStyle: { width: 2, color: '#f59e0b', type: 'dashed' },
        itemStyle: { color: '#f59e0b' },
      },
    ],
  })
}

function handleWindowResize(): void {
  map?.invalidateSize()
  chart?.resize()
}

onMounted(async () => {
  window.addEventListener('resize', handleWindowResize)
  await loadDashboardData()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleWindowResize)
  map?.remove()
  chart?.dispose()
})
</script>

<template>
  <div class="mx-auto max-w-7xl px-4 py-5 sm:px-6">

    <!-- Error banner -->
    <section
      v-if="errorMessage"
      class="mb-5 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4"
      role="alert"
      aria-live="assertive"
    >
      <svg class="mt-0.5 h-5 w-5 shrink-0 text-red-500" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm-.75-11.25a.75.75 0 011.5 0v4.5a.75.75 0 01-1.5 0v-4.5zm.75 7.5a.875.875 0 110-1.75.875.875 0 010 1.75z" clip-rule="evenodd"/>
      </svg>
      <div class="flex-1">
        <p class="text-sm font-medium text-red-800">{{ errorMessage }}</p>
      </div>
      <button
        class="rounded-lg bg-red-100 px-3 py-1.5 text-xs font-semibold text-red-700 transition hover:bg-red-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500"
        @click="loadDashboardData"
      >
        Retry
      </button>
    </section>

    <!-- Skeleton loaders -->
    <section
      v-if="loading"
      class="grid grid-cols-1 gap-5 lg:grid-cols-2"
      aria-busy="true"
      aria-label="Loading dashboard data"
    >
      <div v-for="n in 2" :key="n" class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div class="border-b border-slate-100 px-5 py-4">
          <div class="skeleton h-4 w-40 rounded"></div>
        </div>
        <div class="p-4">
          <div class="skeleton h-[clamp(380px,45vh,540px)] w-full rounded-lg"></div>
        </div>
      </div>
    </section>

    <!-- Dashboard panels -->
    <section v-else-if="!errorMessage" class="grid grid-cols-1 gap-5 lg:grid-cols-2">

      <!-- Map panel -->
      <article class="flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div class="border-b border-slate-100 px-5 py-4">
          <h2 class="text-sm font-semibold text-slate-800">5G Network Coverage Map</h2>
          <p class="mt-0.5 text-xs text-slate-500">Signal quality by geographic square — Brimbank, Melbourne</p>
        </div>
        <div class="flex-1 p-3">
          <div ref="mapContainerRef" class="map-container h-[clamp(380px,45vh,540px)] w-full overflow-hidden rounded-lg"></div>
        </div>
        <div class="flex flex-wrap items-center gap-4 border-t border-slate-100 px-5 py-3">
          <span class="text-xs font-medium text-slate-500">Signal Quality:</span>
          <div v-for="item in qualityLegend" :key="item.label" class="flex items-center gap-1.5">
            <span class="inline-block h-2.5 w-2.5 rounded-full" :style="{ backgroundColor: item.color }"></span>
            <span class="text-xs text-slate-700">{{ item.label }}</span>
            <span class="text-xs text-slate-400">({{ item.sublabel }})</span>
          </div>
        </div>
      </article>

      <!-- Chart panel -->
      <article class="flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div class="border-b border-slate-100 px-5 py-4">
          <h2 class="text-sm font-semibold text-slate-800">5G Predicted Throughput</h2>
          <p class="mt-0.5 text-xs text-slate-500">Forecast speed and latency over time</p>
        </div>
        <div class="flex-1 p-3">
          <div ref="chartContainerRef" class="h-[clamp(380px,45vh,540px)] w-full"></div>
        </div>
      </article>

    </section>
  </div>
</template>

<style scoped>
.skeleton {
  background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.map-container :deep(.leaflet-container) {
  height: 100%;
  width: 100%;
  border-radius: 0.5rem;
}
</style>
