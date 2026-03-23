<script setup lang="ts">
import { ref } from 'vue'

interface FlowStep {
  id: number
  title: string
  description: string
}

const trainingSteps: FlowStep[] = [
  { id: 1, title: 'New 5G CSV Data',           description: 'A new [Date]-truck-combined-kml.csv is uploaded to S3 Raw Data.' },
  { id: 2, title: 'S3 Event Notification',      description: 'S3 Raw Data detects the new object and sends an event notification.' },
  { id: 3, title: 'AWS Lambda Trigger',         description: 'The S3 Event triggers an AWS Lambda function to start the MLOps pipeline.' },
  { id: 4, title: 'SageMaker Processing',       description: 'A temporary containerized job runs. It reads the raw CSV, removes 99999 coordinates / 1000 timeouts, and extracts features.' },
  { id: 5, title: 'Merge with Feature Store',   description: 'The cleaned data is merged into the historical dataset stored in S3.' },
  { id: 6, title: 'SageMaker Training & Eval',  description: 'Trains new clustering (Map) and time-series (Forecast) models using a rolling window of recent data. Evaluates the new Challenger vs current Champion.' },
  { id: 7, title: 'Model Registry (Artifacts)', description: 'If the Challenger is better, the approved .pkl artifacts are versioned and stored securely in S3.' },
]

const inferenceSteps: FlowStep[] = [
  { id: 1, title: 'Dashboard Access',         description: 'A user accesses the 5G Network Quality Dashboard in their browser.' },
  { id: 2, title: 'CloudFront CDN',           description: 'Securely serves the static Vue 3 application assets (HTML / CSS / JS) to the client.' },
  { id: 3, title: 'App Runner FastAPI',        description: 'The Vue frontend makes an API call to /api/map-data. The FastAPI backend receives the request.' },
  { id: 4, title: 'S3 Artifacts (Load Model)','description': 'The FastAPI backend downloads the latest approved .pkl model artifacts from S3 into its local memory.' },
  { id: 5, title: 'Live Predictions',          description: 'The backend runs inference using the model, returning live GeoJSON / forecast data to the Vue chart and map.' },
]

const isTrainingSimulating = ref(false)
const isInferenceSimulating = ref(false)
const activeTrainingStep = ref(0)
const activeInferenceStep = ref(0)

function simulateTraining(): void {
  if (isTrainingSimulating.value || isInferenceSimulating.value) return
  isTrainingSimulating.value = true
  activeTrainingStep.value = 0
  trainingSteps.forEach((_, i) => {
    setTimeout(() => {
      activeTrainingStep.value = i + 1
      if (i === trainingSteps.length - 1) {
        setTimeout(() => {
          isTrainingSimulating.value = false
          activeTrainingStep.value = 0
        }, 1800)
      }
    }, (i + 1) * 1300)
  })
}

function simulateInference(): void {
  if (isTrainingSimulating.value || isInferenceSimulating.value) return
  isInferenceSimulating.value = true
  activeInferenceStep.value = 0
  inferenceSteps.forEach((_, i) => {
    setTimeout(() => {
      activeInferenceStep.value = i + 1
      if (i === inferenceSteps.length - 1) {
        setTimeout(() => {
          isInferenceSimulating.value = false
          activeInferenceStep.value = 0
        }, 1800)
      }
    }, (i + 1) * 1300)
  })
}
</script>

<template>
  <div class="w-full rounded-2xl border border-slate-200 bg-white shadow-sm">

    <div class="grid grid-cols-1 gap-12 p-8 lg:grid-cols-2">

      <!-- ── Column 1: Continuous Training Flow ── -->
      <div class="flex flex-col">

        <!-- Column header + button -->
        <div class="mb-6 flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <span class="inline-block rounded-full bg-violet-100 px-3 py-0.5 text-xs font-bold uppercase tracking-widest text-violet-700">MLOps</span>
            <h3 class="mt-2 text-base font-bold text-slate-800">Continuous Training Flow</h3>
          </div>
          <button
            class="shrink-0 rounded-lg px-4 py-2 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-500"
            :class="(isTrainingSimulating || isInferenceSimulating)
              ? 'cursor-not-allowed bg-slate-100 text-slate-400'
              : 'bg-violet-600 text-white hover:bg-violet-700 active:scale-95'"
            :disabled="isTrainingSimulating || isInferenceSimulating"
            @click="simulateTraining"
          >
            <span class="flex items-center gap-1.5">
              <svg v-if="!isTrainingSimulating" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z"/>
              </svg>
              <svg v-else class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"/>
              </svg>
              Simulate Model Training
            </span>
          </button>
        </div>

        <!-- Training steps -->
        <div class="flex flex-col">
          <template v-for="(step, index) in trainingSteps" :key="step.id">

            <div
              class="w-full flex flex-col rounded-xl border-2 p-6 shadow-sm transition-all duration-500"
              :class="activeTrainingStep === step.id
                ? 'border-orange-500 bg-orange-50 ring-4 ring-orange-500 ring-offset-2 shadow-lg'
                : activeTrainingStep > step.id
                  ? 'border-emerald-200 bg-emerald-50/60'
                  : 'border-slate-200 bg-white'"
            >
              <div class="mb-2 flex items-center gap-2">
                <span
                  class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold"
                  :class="activeTrainingStep === step.id
                    ? 'bg-orange-500 text-white'
                    : activeTrainingStep > step.id
                      ? 'bg-emerald-500 text-white'
                      : 'bg-slate-200 text-slate-500'"
                >
                  <svg v-if="activeTrainingStep > step.id" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/>
                  </svg>
                  <span v-else>{{ step.id }}</span>
                </span>
                <p class="text-sm font-bold text-slate-800">{{ step.title }}</p>
                <span v-if="activeTrainingStep === step.id" class="ml-auto inline-flex items-center gap-1 rounded-full bg-orange-100 px-2 py-0.5 text-xs font-semibold text-orange-700">
                  <span class="h-1.5 w-1.5 animate-ping rounded-full bg-orange-500"></span>
                  Active
                </span>
              </div>
              <p class="text-sm leading-relaxed text-slate-600">{{ step.description }}</p>
            </div>

            <!-- Vertical connector (not after last card) -->
            <div v-if="index < trainingSteps.length - 1" class="flex flex-col items-center py-1" aria-hidden="true">
              <div
                class="h-5 w-0.5 transition-colors duration-500"
                :class="activeTrainingStep > step.id ? 'bg-emerald-400' : 'bg-slate-200'"
              ></div>
              <svg
                class="h-2.5 w-2.5 transition-colors duration-500"
                :class="activeTrainingStep > step.id ? 'text-emerald-400' : 'text-slate-300'"
                viewBox="0 0 10 6" fill="currentColor"
              >
                <path d="M0 0 L10 0 L5 6 Z"/>
              </svg>
            </div>

          </template>
        </div>
      </div>

      <!-- ── Column 2: User Inference Flow ── -->
      <div class="flex flex-col">

        <!-- Column header + button -->
        <div class="mb-6 flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <span class="inline-block rounded-full bg-sky-100 px-3 py-0.5 text-xs font-bold uppercase tracking-widest text-sky-700">Live</span>
            <h3 class="mt-2 text-base font-bold text-slate-800">User Inference Flow</h3>
          </div>
          <button
            class="shrink-0 rounded-lg px-4 py-2 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-500"
            :class="(isTrainingSimulating || isInferenceSimulating)
              ? 'cursor-not-allowed bg-slate-100 text-slate-400'
              : 'bg-sky-500 text-white hover:bg-sky-600 active:scale-95'"
            :disabled="isTrainingSimulating || isInferenceSimulating"
            @click="simulateInference"
          >
            <span class="flex items-center gap-1.5">
              <svg v-if="!isInferenceSimulating" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z"/>
              </svg>
              <svg v-else class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"/>
              </svg>
              Simulate User Request
            </span>
          </button>
        </div>

        <!-- Inference steps -->
        <div class="flex flex-col">
          <template v-for="(step, index) in inferenceSteps" :key="step.id">

            <div
              class="w-full flex flex-col rounded-xl border-2 p-6 shadow-sm transition-all duration-500"
              :class="activeInferenceStep === step.id
                ? 'border-orange-500 bg-orange-50 ring-4 ring-orange-500 ring-offset-2 shadow-lg'
                : activeInferenceStep > step.id
                  ? 'border-emerald-200 bg-emerald-50/60'
                  : 'border-slate-200 bg-white'"
            >
              <div class="mb-2 flex items-center gap-2">
                <span
                  class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold"
                  :class="activeInferenceStep === step.id
                    ? 'bg-orange-500 text-white'
                    : activeInferenceStep > step.id
                      ? 'bg-emerald-500 text-white'
                      : 'bg-slate-200 text-slate-500'"
                >
                  <svg v-if="activeInferenceStep > step.id" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/>
                  </svg>
                  <span v-else>{{ step.id }}</span>
                </span>
                <p class="text-sm font-bold text-slate-800">{{ step.title }}</p>
                <span v-if="activeInferenceStep === step.id" class="ml-auto inline-flex items-center gap-1 rounded-full bg-orange-100 px-2 py-0.5 text-xs font-semibold text-orange-700">
                  <span class="h-1.5 w-1.5 animate-ping rounded-full bg-orange-500"></span>
                  Active
                </span>
              </div>
              <p class="text-sm leading-relaxed text-slate-600">{{ step.description }}</p>
            </div>

            <!-- Vertical connector (not after last card) -->
            <div v-if="index < inferenceSteps.length - 1" class="flex flex-col items-center py-1" aria-hidden="true">
              <div
                class="h-5 w-0.5 transition-colors duration-500"
                :class="activeInferenceStep > step.id ? 'bg-emerald-400' : 'bg-slate-200'"
              ></div>
              <svg
                class="h-2.5 w-2.5 transition-colors duration-500"
                :class="activeInferenceStep > step.id ? 'text-emerald-400' : 'text-slate-300'"
                viewBox="0 0 10 6" fill="currentColor"
              >
                <path d="M0 0 L10 0 L5 6 Z"/>
              </svg>
            </div>

          </template>
        </div>
      </div>

    </div>
  </div>
</template>
