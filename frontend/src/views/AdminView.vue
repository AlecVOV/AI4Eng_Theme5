<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { supabase } from '../services/supabase'

const router = useRouter()

const userEmail = ref('')
const csvFile = ref<File | null>(null)
const uploading = ref(false)
const uploadStatus = ref<{ ok: boolean; message: string } | null>(null)

interface CleanedDataset {
  name: string
  size: string
  date: string
}

interface ModelArtifact {
  version: string
  file: string
  date: string
  accuracy: string
}

// Mock data — replace with axios calls once backend is ready
const cleanedDatasets = ref<CleanedDataset[]>([
  { name: '2026-03-15-truck-combined-cleaned.csv', size: '4.2 MB', date: '2026-03-15' },
  { name: '2026-03-22-truck-combined-cleaned.csv', size: '3.8 MB', date: '2026-03-22' },
  { name: '2026-03-28-truck-combined-cleaned.csv', size: '5.1 MB', date: '2026-03-28' },
])

const modelArtifacts = ref<ModelArtifact[]>([
  { version: 'v1.0.0', file: 'kmeans_v1.0.0.pkl', date: '2026-03-16', accuracy: '92.4%' },
  { version: 'v1.1.0', file: 'kmeans_v1.1.0.pkl', date: '2026-03-23', accuracy: '94.1%' },
  { version: 'v1.2.0', file: 'kmeans_v1.2.0.pkl', date: '2026-03-29', accuracy: '95.7%' },
])

// const API = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
//
// async function fetchCleanedData(): Promise<void> {
//   const { data } = await axios.get<CleanedDataset[]>(`${API}/api/cleaned-data`)
//   cleanedDatasets.value = data
// }
//
// async function fetchModels(): Promise<void> {
//   const { data } = await axios.get<ModelArtifact[]>(`${API}/api/models`)
//   modelArtifacts.value = data
// }

onMounted(async () => {
  const { data } = await supabase.auth.getUser()
  userEmail.value = data.user?.email ?? 'Admin'
  // fetchCleanedData()
  // fetchModels()
})

function onFileChange(event: Event): void {
  const target = event.target as HTMLInputElement
  csvFile.value = target.files?.[0] ?? null
  uploadStatus.value = null
}

async function handleUpload(): Promise<void> {
  if (!csvFile.value) return
  uploading.value = true
  uploadStatus.value = null

  // Mock upload — replace with real API call
  // const formData = new FormData()
  // formData.append('file', csvFile.value)
  // await axios.post(`${API}/api/upload`, formData)

  await new Promise((resolve) => setTimeout(resolve, 1500))
  uploadStatus.value = { ok: true, message: `"${csvFile.value.name}" queued for pipeline processing.` }
  csvFile.value = null

  const input = document.getElementById('csv-upload') as HTMLInputElement | null
  if (input) input.value = ''

  uploading.value = false
}

async function handleSignOut(): Promise<void> {
  await supabase.auth.signOut()
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen bg-slate-50">

    <!-- Top Nav -->
    <header class="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div class="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
        <div class="flex items-center gap-3">
          <h1 class="text-lg font-bold text-slate-900">Admin Panel</h1>
          <span class="rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-semibold text-orange-700">Protected</span>
        </div>
        <div class="flex items-center gap-4">
          <span class="text-sm text-slate-500">{{ userEmail }}</span>
          <button
            class="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-100 active:scale-95"
            @click="handleSignOut"
          >
            Sign Out
          </button>
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-7xl px-6 py-8">

      <!-- Section 1: Data Upload -->
      <section class="mb-10">
        <h2 class="mb-4 text-lg font-semibold text-slate-800">Data Upload — Trigger Pipeline</h2>

        <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <p class="mb-4 text-sm text-slate-600">
            Upload a new 5G drive-test CSV. The file will be sent to the S3 Raw Data bucket, triggering the
            automated SageMaker retraining pipeline.
          </p>

          <div class="flex flex-col gap-4 sm:flex-row sm:items-end">
            <div class="flex-1">
              <label for="csv-upload" class="mb-1 block text-sm font-medium text-slate-700">Select CSV File</label>
              <input
                id="csv-upload"
                type="file"
                accept=".csv"
                class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-orange-50 file:px-3 file:py-1 file:text-sm file:font-medium file:text-orange-700 hover:file:bg-orange-100"
                @change="onFileChange"
              />
            </div>
            <button
              :disabled="!csvFile || uploading"
              class="shrink-0 rounded-lg px-5 py-2.5 text-sm font-semibold text-white transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-500"
              :class="(!csvFile || uploading) ? 'cursor-not-allowed bg-slate-300' : 'bg-orange-500 hover:bg-orange-600 active:scale-95'"
              @click="handleUpload"
            >
              <span class="flex items-center gap-1.5">
                <svg
                  v-if="uploading"
                  class="h-4 w-4 animate-spin"
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
                  aria-hidden="true"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"/>
                </svg>
                {{ uploading ? 'Uploading…' : 'Upload to S3 Pipeline' }}
              </span>
            </button>
          </div>

          <!-- Status -->
          <div
            v-if="uploadStatus"
            class="mt-4 rounded-lg px-4 py-3 text-sm"
            :class="uploadStatus.ok ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'"
          >
            {{ uploadStatus.message }}
          </div>
        </div>
      </section>

      <!-- Section 2: Artifact & Data Viewer -->
      <section>
        <h2 class="mb-4 text-lg font-semibold text-slate-800">Artifact &amp; Data Viewer</h2>

        <div class="grid gap-6 lg:grid-cols-2">

          <!-- Left: Cleaned Data -->
          <div class="rounded-xl border border-slate-200 bg-white shadow-sm">
            <div class="border-b border-slate-100 px-6 py-4">
              <h3 class="text-sm font-bold uppercase tracking-wide text-slate-500">Cleaned Datasets (S3)</h3>
            </div>
            <div class="divide-y divide-slate-100">
              <div
                v-for="ds in cleanedDatasets"
                :key="ds.name"
                class="flex items-center justify-between px-6 py-3.5"
              >
                <div>
                  <p class="text-sm font-medium text-slate-800">{{ ds.name }}</p>
                  <p class="text-xs text-slate-400">{{ ds.date }}</p>
                </div>
                <span class="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">{{ ds.size }}</span>
              </div>
              <div v-if="cleanedDatasets.length === 0" class="px-6 py-8 text-center text-sm text-slate-400">
                No cleaned datasets found.
              </div>
            </div>
          </div>

          <!-- Right: Model Registry -->
          <div class="rounded-xl border border-slate-200 bg-white shadow-sm">
            <div class="border-b border-slate-100 px-6 py-4">
              <h3 class="text-sm font-bold uppercase tracking-wide text-slate-500">Model Registry (S3 Artifacts)</h3>
            </div>
            <div class="divide-y divide-slate-100">
              <div
                v-for="model in modelArtifacts"
                :key="model.version"
                class="flex items-center justify-between px-6 py-3.5"
              >
                <div>
                  <p class="text-sm font-medium text-slate-800">
                    {{ model.file }}
                    <span class="ml-1.5 rounded bg-emerald-50 px-1.5 py-0.5 text-xs font-semibold text-emerald-700">{{ model.version }}</span>
                  </p>
                  <p class="text-xs text-slate-400">{{ model.date }}</p>
                </div>
                <span class="rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">{{ model.accuracy }}</span>
              </div>
              <div v-if="modelArtifacts.length === 0" class="px-6 py-8 text-center text-sm text-slate-400">
                No model artifacts found.
              </div>
            </div>
          </div>

        </div>
      </section>

    </main>
  </div>
</template>
