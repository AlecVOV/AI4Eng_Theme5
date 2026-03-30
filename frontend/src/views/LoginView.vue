<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { supabase } from '../services/supabase'

const router = useRouter()

const email = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function handleSignIn(): Promise<void> {
  loading.value = true
  errorMsg.value = ''

  const { error } = await supabase.auth.signInWithPassword({
    email: email.value,
    password: password.value,
  })

  loading.value = false

  if (error) {
    errorMsg.value = error.message
    return
  }

  router.push('/admin')
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-slate-50 px-4">
    <div class="w-full max-w-sm">

      <!-- Card -->
      <div class="rounded-2xl border border-slate-200 bg-white p-8 shadow-lg">

        <!-- Header -->
        <div class="mb-8 text-center">
          <h1 class="text-2xl font-bold text-slate-900">Admin Sign In</h1>
          <p class="mt-1 text-sm text-slate-500">5G Network Quality Dashboard</p>
        </div>

        <!-- Error banner -->
        <div
          v-if="errorMsg"
          class="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 border border-red-200"
          role="alert"
        >
          {{ errorMsg }}
        </div>

        <!-- Form -->
        <form @submit.prevent="handleSignIn" class="flex flex-col gap-4">
          <div>
            <label for="email" class="mb-1 block text-sm font-medium text-slate-700">Email</label>
            <input
              id="email"
              v-model="email"
              type="email"
              required
              autocomplete="email"
              placeholder="admin@example.com"
              class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30"
            />
          </div>

          <div>
            <label for="password" class="mb-1 block text-sm font-medium text-slate-700">Password</label>
            <input
              id="password"
              v-model="password"
              type="password"
              required
              autocomplete="current-password"
              placeholder="••••••••"
              class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/30"
            />
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="mt-2 flex w-full items-center justify-center rounded-lg bg-orange-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-orange-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <svg
              v-if="loading"
              class="mr-2 h-4 w-4 animate-spin"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
              aria-hidden="true"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
              />
            </svg>
            {{ loading ? 'Signing in…' : 'Sign In' }}
          </button>
        </form>
      </div>

      <!-- Back link -->
      <p class="mt-6 text-center text-sm text-slate-400">
        <router-link to="/" class="hover:text-slate-600 transition">&larr; Back to Dashboard</router-link>
      </p>
    </div>
  </div>
</template>
