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
    name: 'Le Hoang Triet Thong',
    role: 'ML Engineer',
    school: 'Swinburne University of Technology',
    major: 'Bachelor of Computer Science (Artificial Intelligence)',
    bio: 'Full-stack AI engineer who single-handedly designed and built the entire 5G Network Quality Dashboard — from raw data preprocessing and model training through to a production Vue 3 frontend, FastAPI backend, and a fully automated AWS serverless deployment. Driven by a passion for turning messy network telemetry into actionable, real-time insights.',
    contributions: [
      'Preprocessed 138 raw 5G drive-test CSVs — cleaned invalid GPS coordinates, removed timeout values, and engineered features for model training',
      'Trained a KMeans clustering model (with StandardScaler) to classify 5G signal quality into three tiers: Tốt, Trung bình, and Yếu',
      'Built an XGBoost time-series forecasting model with Optuna hyperparameter tuning for throughput and latency prediction',
      'Developed the FastAPI backend with endpoints for map data, forecast data, contact email (Resend), and S3 artifact listing (boto3)',
      'Built the full Vue 3 SPA with 7 routes — interactive Leaflet map, ECharts dual-axis chart, About page, Architecture page, Contact form, Login, and Admin panel',
      'Implemented Supabase authentication with JWT-protected admin routes and a Vue Router auth guard',
      'Designed the responsive UI with Tailwind CSS v4, custom design tokens, scroll-reveal animations, skeleton loaders, and accessibility features',
      'Created interactive Architecture page components — animated MLOps Pipeline timeline and AWS Architecture Map with step-by-step simulation',
      'Containerised the full stack with Docker Compose (multi-stage frontend build + Python backend), plus a Lambda-specific Dockerfile for production',
      'Deployed backend to AWS Lambda (ECR container + Mangum) behind API Gateway, and frontend to S3 + CloudFront with OAC',
      'Authored the complete AWS Deployment Plan covering IAM roles, S3 buckets, SageMaker pipeline definition, ECR/Lambda/API Gateway setup, and CloudFront distribution',
    ],
    avatarInitials: 'LHTT',
    avatarColor: 'bg-sky-400',
  },
  {
    number: '02',
    name: 'Vu Thanh Phong',
    role: 'Data Analyst',
    school: 'Swinburne University of Technology',
    major: 'Bachelor of Computer Science (Artificial Intelligence)',
    bio: 'Enjoy working with data.',
    contributions: [
      'Supported in data processing and EDA',
      'Supported in training ML models',
    ],
    avatarInitials: 'VTP',
    avatarColor: 'bg-orange-500',
  },
  {
    number: '03',
    name: 'Nguyen Tai Minh Huy',
    role: 'AI Developer',
    school: 'Swinburne University of Technology',
    major: 'Bachelor of Computer Science (Artificial Intelligence)',
    bio: 'Passionate about Artificial Intelligence and its real-world applications. Interested in machine learning, deep learning, and data-driven solutions that solve complex problems. Currently exploring AI techniques including neural networks, ensemble methods, and time-series forecasting to push the boundaries of what intelligent systems can achieve.',
    contributions: [
      'Check the ML pipeline for 5G upload bitrate prediction',
      'Trained and compared Random Forest, XGBoost, LSTM, GRU, and Mamba-SSM models',
      'Implemented ensemble methods combining tabular and deep learning models',
    ],
    avatarInitials: 'NTMH',
    avatarColor: 'bg-orange-500',
  },
  {
    number: '04',
    name: 'Le Minh Kha',
    role: 'Data Analyst',
    school: 'Swinburne University of Technology',
    major: 'Bachelor of Computer Science (Artificial Intelligence)',
    bio: 'Enjoy working with data.',
    contributions: [
      'Supported in data processing and EDA',
      'Supported in training ML models',
    ],
    avatarInitials: 'LMK',
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
