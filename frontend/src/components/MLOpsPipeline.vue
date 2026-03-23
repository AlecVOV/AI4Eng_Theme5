<script setup lang="ts">
import { ref } from 'vue'

interface PipelineNode {
  id: number
  label: string
  sublabel: string
  description: string
  icon: string
  accentColor: string
  accentBorder: string
  accentRing: string
  accentText: string
  accentBg: string
}

const nodes: PipelineNode[] = [
  {
    id: 1,
    label: 'S3 Raw Data',
    sublabel: 'User Upload',
    description: 'New 5G performance CSVs (throughput, latency, GPS) are uploaded to the S3 bucket, triggering an event notification.',
    icon: 'M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5',
    accentColor: 'bg-sky-500',
    accentBorder: 'border-sky-500',
    accentRing: 'ring-sky-400',
    accentText: 'text-sky-700',
    accentBg: 'bg-sky-50',
  },
  {
    id: 2,
    label: 'SageMaker Processing',
    sublabel: 'Merge Old + New Data',
    description: 'A containerized job cleans invalid coordinates (99999) and timeouts, appending the clean data to the historical feature store.',
    icon: 'M19.5 12c0-1.232-.046-2.453-.138-3.662a4.006 4.006 0 00-3.7-3.7 48.678 48.678 0 00-7.324 0 4.006 4.006 0 00-3.7 3.7c-.017.22-.032.441-.046.662M19.5 12l3-3m-3 3l-3-3m-12 3c0 1.232.046 2.453.138 3.662a4.006 4.006 0 003.7 3.7 48.656 48.656 0 007.324 0 4.006 4.006 0 003.7-3.7c.017-.22.032-.441.046-.662M4.5 12l3 3m-3-3l-3 3',
    accentColor: 'bg-indigo-500',
    accentBorder: 'border-indigo-500',
    accentRing: 'ring-indigo-400',
    accentText: 'text-indigo-700',
    accentBg: 'bg-indigo-50',
  },
  {
    id: 3,
    label: 'SageMaker Training',
    sublabel: 'Rolling Window',
    description: 'Trains new K-Means and Time-Series models using a rolling window of recent data to capture the latest network degradation trends.',
    icon: 'M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z',
    accentColor: 'bg-violet-500',
    accentBorder: 'border-violet-500',
    accentRing: 'ring-violet-400',
    accentText: 'text-violet-700',
    accentBg: 'bg-violet-50',
  },
  {
    id: 4,
    label: 'Evaluation',
    sublabel: 'Champion vs. Challenger',
    description: 'The new Challenger model is evaluated against the current Champion model using silhouette scores and RMSE.',
    icon: 'M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zm6.75-4.875C9.75 7.504 10.254 7 10.875 7h2.25c.621 0 1.125.504 1.125 1.125V19.875c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.25zm6.75-3c0-.621.504-1.125 1.125-1.125h2.25C20.496 4.125 21 4.629 21 5.25V19.875c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V5.25z',
    accentColor: 'bg-amber-500',
    accentBorder: 'border-amber-500',
    accentRing: 'ring-amber-400',
    accentText: 'text-amber-700',
    accentBg: 'bg-amber-50',
  },
  {
    id: 5,
    label: 'Model Registry',
    sublabel: 'S3 Artifacts',
    description: 'If the Challenger outperforms, the approved .pkl artifacts are versioned and stored securely in the S3 artifact bucket.',
    icon: 'M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125',
    accentColor: 'bg-emerald-500',
    accentBorder: 'border-emerald-500',
    accentRing: 'ring-emerald-400',
    accentText: 'text-emerald-700',
    accentBg: 'bg-emerald-50',
  },
  {
    id: 6,
    label: 'Live API',
    sublabel: 'FastAPI',
    description: 'The FastAPI backend pulls the new artifacts into memory, serving updated predictions to the dashboard with zero downtime.',
    icon: 'M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z',
    accentColor: 'bg-teal-500',
    accentBorder: 'border-teal-500',
    accentRing: 'ring-teal-400',
    accentText: 'text-teal-700',
    accentBg: 'bg-teal-50',
  },
]

const activeStep = ref(0)
const isRunning = ref(false)

function isActive(nodeId: number): boolean {
  return activeStep.value === nodeId
}

function isDone(nodeId: number): boolean {
  return activeStep.value > nodeId
}

function runSimulation(): void {
  if (isRunning.value) return
  isRunning.value = true
  activeStep.value = 0

  nodes.forEach((node, index) => {
    setTimeout(() => {
      activeStep.value = node.id
      if (index === nodes.length - 1) {
        // After the last step, pause then reset
        setTimeout(() => {
          isRunning.value = false
        }, 2000)
      }
    }, (index + 1) * 1500)
  })
}

function reset(): void {
  if (isRunning.value) return
  activeStep.value = 0
}
</script>

<template>
  <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">

    <!-- Header + controls -->
    <div class="mb-6 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
      <div>
        <h3 class="text-base font-semibold text-slate-800">MLOps Continuous Training Pipeline</h3>
        <p class="mt-0.5 text-sm text-slate-500">Click the button to simulate a new data upload triggering the full pipeline.</p>
      </div>
      <div class="flex shrink-0 items-center gap-2">
        <button
          class="rounded-lg px-4 py-2 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-500"
          :class="isRunning
            ? 'cursor-not-allowed bg-slate-100 text-slate-400'
            : 'bg-orange-500 text-white hover:bg-orange-600 active:scale-95'"
          :disabled="isRunning"
          @click="runSimulation"
        >
          <span class="flex items-center gap-1.5">
            <svg v-if="!isRunning" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z"/>
            </svg>
            <svg v-else class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"/>
            </svg>
            {{ isRunning ? 'Running…' : 'Simulate New Data Upload' }}
          </span>
        </button>
        <button
          v-if="activeStep > 0 && !isRunning"
          class="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 transition hover:bg-slate-50"
          @click="reset"
        >
          Reset
        </button>
      </div>
    </div>

    <!-- Progress bar -->
    <div class="mb-6">
      <div class="mb-1.5 flex items-center justify-between text-xs text-slate-500">
        <span>Pipeline progress</span>
        <span class="font-medium text-slate-700">{{ Math.round((activeStep / nodes.length) * 100) }}%</span>
      </div>
      <div class="h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div
          class="h-full rounded-full bg-gradient-to-r from-orange-400 to-emerald-500 transition-all duration-700 ease-out"
          :style="{ width: `${(activeStep / nodes.length) * 100}%` }"
          role="progressbar"
          :aria-valuenow="activeStep"
          :aria-valuemax="nodes.length"
        ></div>
      </div>
    </div>

    <!-- Vertical timeline -->
    <div class="flex flex-col space-y-4">
      <div
        v-for="node in nodes"
        :key="node.id"
        class="w-full flex flex-row items-start gap-5 rounded-xl border-2 p-6 transition-all duration-500"
        :class="[
          isActive(node.id)
            ? [node.accentBorder, node.accentBg, 'shadow-md']
            : isDone(node.id)
              ? 'border-emerald-200 bg-emerald-50/60 shadow-sm'
              : 'border-slate-200 bg-white shadow-sm',
        ]"
      >
        <!-- Icon badge -->
        <div class="relative shrink-0">
          <div
            class="flex h-12 w-12 items-center justify-center rounded-xl text-white transition-all duration-500"
            :class="isActive(node.id) ? node.accentColor : isDone(node.id) ? 'bg-emerald-400' : 'bg-slate-200'"
          >
            <!-- Pulsing ring for active state -->
            <span
              v-if="isActive(node.id)"
              class="absolute inline-flex h-12 w-12 animate-ping rounded-xl opacity-25"
              :class="node.accentColor"
              aria-hidden="true"
            ></span>
            <!-- Checkmark when done -->
            <svg v-if="isDone(node.id)" class="relative h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/>
            </svg>
            <svg v-else class="relative h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" :d="node.icon"/>
            </svg>
          </div>
        </div>

        <!-- Text content -->
        <div class="flex-1 min-w-0">
          <div class="flex flex-wrap items-center gap-2 mb-1">
            <span
              class="text-xs font-bold uppercase tracking-wide transition-colors duration-300"
              :class="isActive(node.id) ? node.accentText : isDone(node.id) ? 'text-emerald-600' : 'text-slate-400'"
            >Step {{ node.id }}</span>
            <!-- Evaluation tooltip badge -->
            <span
              v-if="node.id === 4 && isActive(4)"
              class="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-800"
              role="status"
              aria-live="polite"
            >Comparing accuracy…</span>
          </div>
          <p class="text-sm font-semibold text-slate-900">{{ node.label }}</p>
          <p class="text-xs text-slate-500 mb-2">{{ node.sublabel }}</p>
          <p class="text-sm text-slate-600 leading-relaxed">{{ node.description }}</p>
        </div>

        <!-- Status indicator -->
        <div class="shrink-0 self-center">
          <span
            v-if="isDone(node.id)"
            class="flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700"
          >
            <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>
            Done
          </span>
          <span
            v-else-if="isActive(node.id)"
            class="flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold"
            :class="[node.accentBg, node.accentText]"
          >
            <svg class="h-3.5 w-3.5 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"/></svg>
            Active
          </span>
          <span
            v-else
            class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-400"
          >Waiting</span>
        </div>
      </div>
    </div>

    <!-- Completion banner -->
    <div
      v-if="activeStep === nodes.length && !isRunning"
      class="mt-6 flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-5 py-4"
      role="status"
      aria-live="polite"
    >
      <svg class="h-5 w-5 shrink-0 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
      <p class="text-sm font-medium text-emerald-800">Pipeline complete. New champion model is live in the API.</p>
    </div>

  </div>
</template>
