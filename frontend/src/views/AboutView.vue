<script setup lang="ts">
import { onMounted, ref } from 'vue'

interface TeamMember {
  number: string
  name: string
  role: string
  school: string
  major: string
  bio: string
  contributions: string[]
  avatarInitials: string
  avatarColor: string
}

const members: TeamMember[] = [
  {
    number: '01',
    name: 'Team Member 1',
    role: 'ML Engineer',
    school: 'Swinburne University of Technology',
    major: 'Bachelor of Computer Science (Artificial Intelligence)',
    bio: 'Passionate about applying machine learning to real-world network optimisation problems. Specialised in clustering algorithms and geospatial data analysis.',
    contributions: [
      'Designed and trained the KMeans clustering model for 5G signal quality classification',
      'Implemented the data preprocessing pipeline and feature engineering',
      'Developed the time-series forecasting model for throughput prediction',
    ],
    avatarInitials: 'TM',
    avatarColor: 'bg-orange-500',
  },
  {
    number: '02',
    name: 'Team Member 2',
    role: 'Backend Developer',
    school: 'Swinburne University of Technology',
    major: 'Bachelor of Computer Science (Artificial Intelligence)',
    bio: 'Focused on building robust, scalable API services. Experienced with Python FastAPI and data serialisation for high-throughput applications.',
    contributions: [
      'Built the FastAPI backend with GeoJSON and forecast endpoints',
      'Integrated trained model artefacts into the API runtime',
      'Configured Docker Compose orchestration for the full stack',
    ],
    avatarInitials: 'TM',
    avatarColor: 'bg-teal-600',
  },
  {
    number: '03',
    name: 'Team Member 3',
    role: 'Frontend Developer',
    school: 'Swinburne University of Technology',
    major: 'Bachelor of Computer Science (Artificial Intelligence)',
    bio: 'Crafts accessible, responsive interfaces with modern web technologies. Enthusiastic about data visualisation and interactive maps.',
    contributions: [
      'Designed and implemented the Vue 3 dashboard with Tailwind CSS v4',
      'Integrated Leaflet map and Apache ECharts for live data visualisation',
      'Built the multi-page SPA with Vue Router and smooth scroll animations',
    ],
    avatarInitials: 'TM',
    avatarColor: 'bg-indigo-600',
  },
  {
    number: '04',
    name: 'Team Member 4',
    role: 'Data Analyst',
    school: 'Swinburne University of Technology',
    major: 'Bachelor of Computer Science (Artificial Intelligence)',
    bio: 'Expert at transforming raw network telemetry into actionable insights. Responsible for dataset sourcing, EDA, and quality validation.',
    contributions: [
      'Sourced and cleaned the 5G coverage dataset from public telecom records',
      'Conducted exploratory data analysis and documented findings',
      'Defined evaluation metrics and validated model performance benchmarks',
    ],
    avatarInitials: 'TM',
    avatarColor: 'bg-rose-600',
  },
]

// Each card gets its own ref for the IntersectionObserver
const cardRefs = ref<HTMLElement[]>([])

function setCardRef(el: HTMLElement | null, index: number) {
  if (el) cardRefs.value[index] = el
}

onMounted(() => {
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible')
          observer.unobserve(entry.target)
        }
      }
    },
    { threshold: 0.12 },
  )

  for (const el of cardRefs.value) {
    if (el) observer.observe(el)
  }
})
</script>

<template>
  <div class="min-h-screen bg-gradient-to-b from-orange-50/60 via-white to-slate-50">

    <!-- Page hero -->
    <section class="border-b border-slate-100 bg-white/80 py-14 text-center backdrop-blur-sm">
      <span class="inline-block rounded-full bg-orange-100 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-orange-600">COS40007 Final Project</span>
      <h1 class="mt-4 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">Meet the Team</h1>
      <p class="mx-auto mt-3 max-w-xl text-base text-slate-500">
        Four AI Engineering students from Swinburne University working together to bring
        5G network quality insights to life.
      </p>
    </section>

    <!-- Team cards -->
    <section class="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <div class="flex flex-col gap-8">
        <div
          v-for="(member, index) in members"
          :key="member.number"
          :ref="(el) => setCardRef(el as HTMLElement | null, index)"
          class="reveal-card relative overflow-hidden rounded-2xl border border-orange-200 bg-white shadow-sm"
        >
          <!-- Faded background number -->
          <span
            class="pointer-events-none absolute right-4 top-2 select-none text-6xl font-black text-orange-500 opacity-10"
            aria-hidden="true"
          >{{ member.number }}</span>

          <div class="flex flex-col gap-6 p-6 sm:flex-row sm:items-start">

            <!-- Avatar placeholder -->
            <div class="flex shrink-0 flex-col items-center gap-2">
              <div
                class="flex h-20 w-20 items-center justify-center rounded-2xl text-2xl font-bold text-white shadow-md"
                :class="member.avatarColor"
              >
                {{ member.avatarInitials }}
              </div>
              <span class="rounded-full bg-orange-500 px-2.5 py-0.5 text-xs font-semibold text-white">
                {{ member.role }}
              </span>
            </div>

            <!-- Details -->
            <div class="flex-1 min-w-0">
              <h2 class="text-lg font-semibold text-slate-900">{{ member.name }}</h2>
              <p class="mt-0.5 text-xs text-slate-500">{{ member.school }}</p>
              <p class="text-xs text-slate-400">{{ member.major }}</p>

              <p class="mt-3 text-sm text-slate-600 leading-relaxed">{{ member.bio }}</p>

              <!-- Contributions -->
              <div class="mt-4 rounded-xl bg-orange-50/70 px-4 py-3">
                <p class="mb-2 text-xs font-semibold uppercase tracking-wide text-orange-700">Key Contributions</p>
                <ul class="space-y-1.5">
                  <li
                    v-for="item in member.contributions"
                    :key="item"
                    class="flex items-start gap-2 text-sm text-slate-700"
                  >
                    <svg class="mt-0.5 h-3.5 w-3.5 shrink-0 text-orange-500" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                      <path fill-rule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clip-rule="evenodd"/>
                    </svg>
                    {{ item }}
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.reveal-card {
  opacity: 0;
  transform: translateY(2.5rem);
  transition: opacity 0.6s ease, transform 0.6s ease;
  will-change: transform, opacity;
}

.reveal-card.is-visible {
  opacity: 1;
  transform: translateY(0);
}
</style>
