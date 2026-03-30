<script setup lang="ts">
</script>

<template>
  <div class="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4 text-center">

    <p class="text-9xl font-black tracking-tight text-orange-500">404</p>

    <h1 class="mt-4 text-2xl font-bold text-slate-900">Page Not Found</h1>

    <p class="mt-2 max-w-md text-sm leading-relaxed text-slate-500">
      Oops! The zone you are looking for has no 5G coverage.
    </p>

    <router-link
      to="/"
      class="mt-8 inline-flex items-center gap-2 rounded-lg bg-orange-500 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-orange-600 active:scale-95 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-500"
    >
      <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18"/>
      </svg>
      Return to Dashboard
    </router-link>

  </div>
</template>
