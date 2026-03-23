<script setup lang="ts">
import { RouterLink } from 'vue-router'

const year = new Date().getFullYear()

const navLinks = [
  { to: '/',             label: 'Dashboard'     },
  { to: '/about',        label: 'About Us'      },
  { to: '/architecture', label: 'Architecture'  },
  { to: '/contact',      label: 'Contact'       },
]
</script>

<template>
  <footer class="mt-auto w-full bg-gray-900 text-gray-300">
    <div class="mx-auto max-w-7xl px-4 py-12 sm:px-6">
      <div class="grid grid-cols-1 gap-8 md:grid-cols-2">


        <div>
          <h3 class="mb-3 text-xs font-semibold uppercase tracking-widest text-gray-500">Navigation</h3>
          <ul class="space-y-2">
            <li v-for="link in navLinks" :key="link.to">
              <RouterLink
                :to="link.to"
                class="text-sm text-gray-400 transition hover:text-white"
              >
                {{ link.label }}
              </RouterLink>
            </li>
          </ul>
        </div>

        <!-- Left: Brand & Info -->
        <div class="flex flex-col items-start">
          <div class="flex items-center gap-2 text-white">
            <svg class="h-5 w-5 text-teal-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M2 20h20"/><path d="M12 20V8"/>
              <path d="M7 15a7 7 0 0 1 10 0"/>
              <path d="M3.5 11.5a13 13 0 0 1 17 0"/>
            </svg>
            <span class="text-sm font-semibold">5G Network Quality Dashboard</span>
          </div>
          <p class="mt-3 text-xs leading-relaxed text-gray-400">
            AI For Engineering Final Project — COS40007.
          </p>
          <p class="mt-2 text-xs leading-relaxed text-gray-400">
            Visualising 5G coverage quality and forecasting throughput with machine learning and deep learning.
          </p>
          <p class="mt-2 text-xs leading-relaxed text-gray-400">
            Built with passion by the Theme 5 group at Swinburne University of Technology.
          </p>
        </div>

        <!-- Right: Navigation -->
        <!-- <div class="flex flex-col items-start md:items-end md:text-right">
          <h3 class="mb-3 text-xs font-semibold uppercase tracking-widest text-gray-500">Navigation</h3>
          <ul class="space-y-2">
            <li v-for="link in navLinks" :key="link.to">
              <RouterLink
                :to="link.to"
                class="text-sm text-gray-400 transition hover:text-white"
              >
                {{ link.label }}
              </RouterLink>
            </li>
          </ul>
        </div> -->

      </div>

      <div class="mt-10 border-t border-gray-800 pt-6 text-center text-xs text-gray-500">
        &copy; {{ year }} Theme 5 — COS40007 — AI For Engineering. All rights reserved.
      </div>
    </div>
  </footer>
</template>
