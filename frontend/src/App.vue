<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import FooterComp from './components/FooterComp.vue'

const mobileMenuOpen = ref(false)

const navLinks = [
  { to: '/',             label: 'Dashboard'    },
  { to: '/about',        label: 'About Us'     },
  { to: '/architecture', label: 'Architecture' },
  { to: '/contact',      label: 'Contact'      },
  { to: '/admin',        label: 'Admin Panel'  },
]

const route = useRoute()
</script>

<template>
  <div class="flex min-h-screen flex-col bg-slate-50">

    <!-- Top navbar -->
    <header class="sticky top-0 z-50 w-full border-b border-slate-200 bg-white/90 backdrop-blur-sm shadow-sm">
      <div class="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">

        <!-- Brand -->
        <RouterLink to="/" class="flex items-center gap-2.5 focus-visible:outline-none">
          <svg class="h-6 w-6 shrink-0 text-teal-700" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M2 20h20"/><path d="M12 20V8"/>
            <path d="M7 15a7 7 0 0 1 10 0"/>
            <path d="M3.5 11.5a13 13 0 0 1 17 0"/>
          </svg>
          <span class="text-base font-semibold tracking-tight text-slate-800">5G Dashboard</span>
        </RouterLink>

        <!-- Desktop nav links -->
        <nav class="hidden items-center gap-1 sm:flex" aria-label="Main navigation">
          <RouterLink
            v-for="link in navLinks"
            :key="link.to"
            :to="link.to"
            class="rounded-lg px-3 py-1.5 text-sm font-medium transition"
            :class="route.path === link.to
              ? 'bg-teal-50 text-teal-700'
              : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'"
          >
            {{ link.label }}
          </RouterLink>
        </nav>

        <!-- Mobile hamburger -->
        <button
          class="flex items-center rounded-lg p-2 text-slate-600 hover:bg-slate-100 sm:hidden"
          aria-label="Toggle navigation menu"
          @click="mobileMenuOpen = !mobileMenuOpen"
        >
          <svg v-if="!mobileMenuOpen" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
          <svg v-else class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12"/></svg>
        </button>
      </div>

      <!-- Mobile dropdown -->
      <nav
        v-if="mobileMenuOpen"
        class="border-t border-slate-100 bg-white px-4 pb-3 sm:hidden"
        aria-label="Mobile navigation"
      >
        <RouterLink
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
          class="block rounded-lg px-3 py-2 text-sm font-medium transition"
          :class="route.path === link.to
            ? 'bg-teal-50 text-teal-700'
            : 'text-slate-600 hover:bg-slate-100'"
          @click="mobileMenuOpen = false"
        >
          {{ link.label }}
        </RouterLink>
      </nav>
    </header>

    <!-- Page content -->
    <main class="flex-1">
      <RouterView />
    </main>

    <!-- Global footer -->
    <FooterComp />

  </div>
</template>

