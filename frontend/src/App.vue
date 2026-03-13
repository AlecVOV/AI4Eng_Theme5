<script setup lang="ts">
import axios from 'axios'
import * as echarts from 'echarts'
import L from 'leaflet'
import { onBeforeUnmount, onMounted, ref } from 'vue'

type MapDataResponse = {
  type: 'FeatureCollection'
  features: Array<{
    type: 'Feature'
    geometry: {
      type: 'Point'
      coordinates: [number, number]
    }
    properties: {
      square_id: string
      quality: string
    }
  }>
}

type ForecastResponse = {
  time: string[]
  predicted_speed_mbps: number[]
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const mapContainerRef = ref<HTMLDivElement | null>(null)
const chartContainerRef = ref<HTMLDivElement | null>(null)
const loading = ref(true)
const errorMessage = ref('')

let map: L.Map | null = null
let chart: echarts.ECharts | null = null

const qualityColorMap: Record<string, string> = {
  Tot: '#17a34a',
  'Trung binh': '#f59e0b',
  Yeu: '#dc2626',
}

async function loadDashboardData() {
  loading.value = true
  errorMessage.value = ''

  try {
    const [mapResponse, forecastResponse] = await Promise.all([
      axios.get<MapDataResponse>(`${apiBaseUrl}/api/map-data`),
      axios.get<ForecastResponse>(`${apiBaseUrl}/api/forecast-data`),
    ])

    renderMap(mapResponse.data)
    renderChart(forecastResponse.data)
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? `Khong the tai du lieu dashboard: ${error.message}`
        : 'Khong the tai du lieu dashboard.'
  } finally {
    loading.value = false
  }
}

function renderMap(data: MapDataResponse) {
  if (!mapContainerRef.value) {
    return
  }

  if (map) {
    map.remove()
  }

  map = L.map(mapContainerRef.value, {
    zoomControl: true,
  }).setView([13.7563, 100.5018], 12)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(map)

  const layer = L.geoJSON(data, {
    pointToLayer: (feature, latlng) => {
      const quality = feature.properties?.quality ?? 'Trung binh'
      const color = qualityColorMap[quality] ?? qualityColorMap['Trung binh']
      return L.circleMarker(latlng, {
        radius: 8,
        fillColor: color,
        color: '#ffffff',
        weight: 1,
        opacity: 1,
        fillOpacity: 0.9,
      })
    },
    onEachFeature: (feature, layerItem) => {
      const properties = feature.properties
      layerItem.bindPopup(
        `<strong>Square:</strong> ${properties.square_id}<br/><strong>Chat luong:</strong> ${properties.quality}`,
      )
    },
  }).addTo(map)

  const bounds = layer.getBounds()
  if (bounds.isValid()) {
    map.fitBounds(bounds.pad(0.2))
  }
}

function renderChart(data: ForecastResponse) {
  if (!chartContainerRef.value) {
    return
  }

  if (chart) {
    chart.dispose()
  }

  chart = echarts.init(chartContainerRef.value)
  chart.setOption({
    grid: {
      left: 40,
      right: 20,
      top: 48,
      bottom: 56,
    },
    tooltip: {
      trigger: 'axis',
    },
    xAxis: {
      type: 'category',
      data: data.time,
      axisLabel: {
        rotate: 30,
      },
    },
    yAxis: {
      type: 'value',
      name: 'Mbps',
    },
    series: [
      {
        name: 'Toc do du bao',
        type: 'line',
        smooth: true,
        data: data.predicted_speed_mbps,
        lineStyle: {
          width: 3,
          color: '#0f766e',
        },
        itemStyle: {
          color: '#0f766e',
        },
        areaStyle: {
          color: 'rgba(15, 118, 110, 0.14)',
        },
      },
    ],
  })
}

function handleWindowResize() {
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
  <main class="dashboard">
    <header class="dashboard__header">
      <h1>5G Network Quality Dashboard</h1>
      <p>Signal 5G Map and chart predicted speed over time</p>
    </header>

    <section v-if="errorMessage" class="state state--error">
      {{ errorMessage }}
    </section>
    <section v-else-if="loading" class="state">Loading data</section>

    <section v-else class="dashboard__grid">
      <article class="panel">
        <h2>5G Network Map</h2>
        <div ref="mapContainerRef" class="panel__body panel__body--map"></div>
      </article>

      <article class="panel">
        <h2>5G Predicted Speed Chart</h2>
        <div ref="chartContainerRef" class="panel__body panel__body--chart"></div>
      </article>
    </section>
  </main>
</template>

<style scoped>
.dashboard {
  min-height: 100vh;
  padding: 1rem;
  box-sizing: border-box;
  background: #f3f6fb;
  color: #1f2937;
}

.dashboard__header {
  margin-bottom: 1rem;
}

.dashboard__header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.dashboard__header p {
  margin: 0.35rem 0 0;
  color: #4b5563;
}

.dashboard__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.panel {
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
}

.panel h2 {
  margin: 0 0 0.65rem;
  font-size: 1rem;
}

.panel__body {
  min-height: 520px;
  border-radius: 8px;
  overflow: hidden;
}

.panel__body--map {
  background: #e5e7eb;
}

.panel__body--chart {
  background: #ffffff;
}

.state {
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 0.75rem;
}

.state--error {
  border-color: #ef4444;
  color: #991b1b;
  background: #fef2f2;
}

@media (max-width: 960px) {
  .dashboard__grid {
    grid-template-columns: 1fr;
  }

  .panel__body {
    min-height: 400px;
  }
}
</style>
