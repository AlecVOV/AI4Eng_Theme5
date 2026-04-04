<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { supabase } from '../services/supabase'

const router = useRouter()

const userEmail = ref('')
const csvFile = ref<File | null>(null)
const uploading = ref(false)
const uploadStatus = ref<{ ok: boolean; message: string } | null>(null)

interface RawDataset {
  name: string
  size: string
  date: string
}

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

const API = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const rawDatasets = ref<RawDataset[]>([])
const rawSearch = ref('')
const cleanedDatasets = ref<CleanedDataset[]>([])
const modelArtifacts = ref<ModelArtifact[]>([])
const loadingData = ref(true)

async function fetchRawData(): Promise<void> {
  try {
    const { data } = await axios.get<RawDataset[]>(`${API}/api/raw-data`)
    rawDatasets.value = data
  } catch {
    rawDatasets.value = []
  }
}

async function fetchCleanedData(): Promise<void> {
  try {
    const { data } = await axios.get<CleanedDataset[]>(`${API}/api/cleaned-data`)
    cleanedDatasets.value = data
  } catch {
    cleanedDatasets.value = []
  }
}

async function fetchModels(): Promise<void> {
  try {
    const { data } = await axios.get<ModelArtifact[]>(`${API}/api/models`)
    modelArtifacts.value = data
  } catch {
    modelArtifacts.value = []
  }
}

onMounted(async () => {
  const { data } = await supabase.auth.getUser()
  userEmail.value = data.user?.email ?? 'Admin'
  await Promise.all([fetchRawData(), fetchCleanedData(), fetchModels()])
  loadingData.value = false
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

        <!-- Raw Datasets — full-width table -->
        <div class="mb-6 rounded-xl border border-slate-200 bg-white shadow-sm">
          <div class="flex items-center justify-between border-b border-slate-100 px-6 py-4">
            <h3 class="text-sm font-bold uppercase tracking-wide text-slate-500">Raw Datasets (S3)</h3>
            <span class="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-600">{{ rawDatasets.length }} files</span>
          </div>
          <div class="px-6 py-3">
            <input
              v-model="rawSearch"
              type="text"
              placeholder="Search files…"
              class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm placeholder:text-slate-400 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>
          <div class="max-h-[28rem] overflow-y-auto">
            <table class="w-full text-left text-sm">
              <thead class="sticky top-0 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th class="px-6 py-3 font-semibold">#</th>
                  <th class="px-6 py-3 font-semibold">File Name</th>
                  <th class="px-6 py-3 font-semibold text-right">Size</th>
                  <th class="px-6 py-3 font-semibold text-right">Last Modified</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr
                  v-for="(ds, idx) in rawDatasets.filter(d => d.name.toLowerCase().includes(rawSearch.toLowerCase()))"
                  :key="ds.name"
                  class="transition hover:bg-slate-50"
                >
                  <td class="px-6 py-3 text-slate-400">{{ idx + 1 }}</td>
                  <td class="px-6 py-3 font-medium text-slate-800">{{ ds.name }}</td>
                  <td class="px-6 py-3 text-right text-slate-600">{{ ds.size }}</td>
                  <td class="px-6 py-3 text-right text-slate-400">{{ ds.date }}</td>
                </tr>
              </tbody>
            </table>
            <div
              v-if="rawDatasets.length === 0"
              class="px-6 py-10 text-center text-sm text-slate-400"
            >
              No raw datasets found in S3.
            </div>
            <div
              v-else-if="rawDatasets.filter(d => d.name.toLowerCase().includes(rawSearch.toLowerCase())).length === 0"
              class="px-6 py-10 text-center text-sm text-slate-400"
            >
              No files match &ldquo;{{ rawSearch }}&rdquo;
            </div>
          </div>
        </div>

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
                <!-- <span class="rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">{{ model.accuracy }}</span> -->
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
