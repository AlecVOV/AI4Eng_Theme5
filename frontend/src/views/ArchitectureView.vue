<script setup lang="ts">
import MLOpsPipeline from '../components/MLOpsPipeline.vue'
import AWSArchitectureMap from '../components/AWSArchitectureMap.vue'

interface Phase {
  number: string
  title: string
  description: string
  tags: string[]
}

interface Layer {
  label: string
  items: { name: string; detail: string }[]
  color: string
  borderColor: string
  badgeColor: string
}

const phases: Phase[] = [
  {
    number: '0',
    title: 'Frontend UI/UX Foundation',
    description: 'Tailwind CSS v4 setup, responsive layout, navbar, panel cards, skeleton loaders, error states, and accessibility primitives.',
    tags: ['Vue 3', 'Tailwind v4', 'Vite'],
  },
  {
    number: '1',
    title: 'Data & Model Pipeline',
    description: 'Dataset preprocessing, KMeans clustering for signal-quality labels, time-series forecasting model, and artefact export.',
    tags: ['scikit-learn', 'pandas', 'numpy'],
  },
  {
    number: '2',
    title: 'Backend Refactor',
    description: 'Split monolithic FastAPI file into routers, services, and schemas. Load model artefacts at startup via lifespan context.',
    tags: ['FastAPI', 'Uvicorn', 'Python 3.10'],
  },
  {
    number: '3',
    title: 'Docker Hardening',
    description: 'Dev vs production Compose overrides, nginx reverse-proxy for CORS elimination, healthchecks, and pinned image versions.',
    tags: ['Docker', 'nginx', 'Compose v2'],
  },
  {
    number: '4',
    title: 'Testing',
    description: 'Backend pytest unit tests for all endpoints. Frontend Cypress E2E specs covering map render, chart render, and error states.',
    tags: ['pytest', 'Cypress', 'Vitest'],
  },
]

const layers: Layer[] = [
  {
    label: 'Frontend',
    items: [
      { name: 'Vue 3 SPA', detail: 'Composition API · <script setup lang="ts">' },
      { name: 'Leaflet Map', detail: 'GeoJSON cluster overlay · OSM tiles' },
      { name: 'Apache ECharts', detail: 'Dual-axis through put / latency chart' },
      { name: 'Tailwind CSS v4', detail: '@tailwindcss/vite · @theme tokens' },
    ],
    color: 'bg-teal-50',
    borderColor: 'border-teal-200',
    badgeColor: 'bg-teal-600',
  },
  {
    label: 'API Layer',
    items: [
      { name: 'FastAPI', detail: 'GET /api/map-data · GET /api/forecast-data' },
      { name: 'Uvicorn', detail: 'ASGI server · port 8000' },
      { name: 'Pydantic', detail: 'Request / response validation' },
      { name: 'CORS Middleware', detail: 'Controlled origin allowlist' },
    ],
    color: 'bg-indigo-50',
    borderColor: 'border-indigo-200',
    badgeColor: 'bg-indigo-600',
  },
  {
    label: 'ML Pipeline',
    items: [
      { name: 'KMeans Clustering', detail: '3 clusters → Tốt / Trung bình / Yếu' },
      { name: 'Feature Engineering', detail: 'RSRP, RSRQ, SINR, throughput bands' },
      { name: 'Time-Series Forecast', detail: 'Predicted throughput (Mbps) + latency (ms)' },
      { name: 'scikit-learn', detail: 'Model artefacts → backend/models/' },
    ],
    color: 'bg-amber-50',
    borderColor: 'border-amber-200',
    badgeColor: 'bg-amber-600',
  },
  {
    label: 'Infrastructure',
    items: [
      { name: 'Docker Compose v2', detail: 'backend + frontend services' },
      { name: 'nginx (frontend)', detail: 'Multi-stage build · port 8080' },
      { name: 'python:3.10-slim', detail: 'Backend container · port 8000' },
      { name: 'Volume mounts', detail: 'data/ · metrics/ · models/' },
    ],
    color: 'bg-slate-50',
    borderColor: 'border-slate-200',
    badgeColor: 'bg-slate-600',
  },
]
</script>

<template>
  <div class="min-h-screen bg-gradient-to-b from-slate-50 to-white">

    <!-- Page hero -->
    <section class="border-b border-slate-100 bg-white/80 py-14 text-center backdrop-blur-sm">
      <span class="inline-block rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-indigo-600">System Design</span>
      <h1 class="mt-4 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">Project Architecture</h1>
      <p class="mx-auto mt-3 max-w-xl text-base text-slate-500">
        An end-to-end AI engineering system that collects 5G telemetry, applies ML clustering and
        forecasting, and visualises results on an interactive dashboard.
      </p>
    </section>

    <div class="mx-auto max-w-5xl px-4 py-12 sm:px-6">

      <!-- The Problem -->
      <section class="mb-14">
        <h2 class="mb-4 text-xl font-semibold text-slate-800">The Problem</h2>
        <div class="grid gap-4 sm:grid-cols-3">
          <div class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-red-100">
              <svg class="h-5 w-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/></svg>
            </div>
            <h3 class="font-semibold text-slate-800">Coverage Gaps</h3>
            <p class="mt-1 text-sm text-slate-500">Identifying poor-signal geographic zones from raw telemetry data without manual inspection.</p>
          </div>
          <div class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100">
              <svg class="h-5 w-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zm6.75-4.875C9.75 7.504 10.254 7 10.875 7h2.25c.621 0 1.125.504 1.125 1.125V19.875c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.25zm6.75-3c0-.621.504-1.125 1.125-1.125h2.25C20.496 4.125 21 4.629 21 5.25V19.875c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V5.25z"/></svg>
            </div>
            <h3 class="font-semibold text-slate-800">Throughput Prediction</h3>
            <p class="mt-1 text-sm text-slate-500">Forecasting future download speeds and latency to allow proactive network planning.</p>
          </div>
          <div class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-teal-100">
              <svg class="h-5 w-5 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 20.25h6M12 3v1.5M5.636 5.636l1.06 1.06M18.364 5.636l-1.061 1.06M3 12h1.5m15 0H21m-2.636 6.364l-1.06-1.06M5.636 18.364l1.06-1.061"/></svg>
            </div>
            <h3 class="font-semibold text-slate-800">Real-Time Visibility</h3>
            <p class="mt-1 text-sm text-slate-500">Presenting insights on an interactive map and time-series chart accessible to non-technical stakeholders.</p>
          </div>
        </div>
      </section>

      <!-- System Architecture — MLOps Pipeline Animation -->
      <section class="mb-14">
        <h2 class="mb-4 text-xl font-semibold text-slate-800">System Architecture</h2>
        <MLOpsPipeline />
      </section>

      <!-- Interactive Cloud Infrastructure Explorer -->
      <section class="mb-14">
        <h2 class="mb-4 text-xl font-semibold text-slate-800">Interactive Cloud Infrastructure Explorer</h2>
        <AWSArchitectureMap />
      </section>

      <!-- Complete System Architecture — Static Diagram -->
      <section class="mb-14">
        <h2 class="mb-4 text-xl font-semibold text-slate-800">Complete System Architecture</h2>
        <div class="w-full h-96 bg-gray-100 border-2 border-dashed border-gray-300 flex items-center justify-center rounded-xl text-gray-500">
          Insert draw.io SVG here
        </div>
      </section>

      <!-- Tech Stack Layers -->
      <section class="mb-14">
        <h2 class="mb-6 text-xl font-semibold text-slate-800">Technology Stack</h2>
        <div class="grid gap-4 sm:grid-cols-2">
          <div
            v-for="layer in layers"
            :key="layer.label"
            class="rounded-2xl border p-5"
            :class="[layer.color, layer.borderColor]"
          >
            <div class="mb-3 flex items-center gap-2">
              <span class="rounded-lg px-2.5 py-0.5 text-xs font-semibold text-white" :class="layer.badgeColor">
                {{ layer.label }}
              </span>
            </div>
            <ul class="space-y-2">
              <li
                v-for="item in layer.items"
                :key="item.name"
                class="flex items-start gap-2"
              >
                <span>
                  <span class="text-sm font-medium text-slate-800">{{ item.name }}</span>
                  <span class="ml-1.5 text-xs text-slate-500">{{ item.detail }}</span>
                </span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <!-- Development Phases -->
      <section>
        <h2 class="mb-6 text-xl font-semibold text-slate-800">Development Roadmap</h2>
        <ol class="relative border-l-2 border-slate-200 pl-6">
          <li
            v-for="phase in phases"
            :key="phase.number"
            class="mb-8 last:mb-0"
          >
            <span class="absolute -left-3.5 flex h-7 w-7 items-center justify-center rounded-full bg-white border-2 border-slate-300 text-xs font-bold text-slate-600 ring-4 ring-white">
              {{ phase.number }}
            </span>
            <h3 class="mb-1 font-semibold text-slate-800">{{ phase.title }}</h3>
            <p class="mb-2 text-sm text-slate-500">{{ phase.description }}</p>
            <div class="flex flex-wrap gap-1.5">
              <span
                v-for="tag in phase.tags"
                :key="tag"
                class="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600"
              >{{ tag }}</span>
            </div>
          </li>
        </ol>
      </section>

    </div>
  </div>
</template>
