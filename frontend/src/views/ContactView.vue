<script setup lang="ts">
import { ref } from 'vue'

interface FormState {
  name: string
  email: string
  message: string
}

interface Link {
  label: string
  href: string
  icon: 'github' | 'linkedin' | 'email'
  description: string
}

const form = ref<FormState>({ name: '', email: '', message: '' })
const submitted = ref(false)
const errors = ref<Partial<FormState>>({})

const links: Link[] = [
  {
    label: 'GitHub Repository',
    href: 'https://github.com',
    icon: 'github',
    description: 'Source code, issues, and pull requests',
  },
  {
    label: 'LinkedIn — Team',
    href: 'https://linkedin.com',
    icon: 'linkedin',
    description: 'Connect with the team on LinkedIn',
  },
  {
    label: 'Email Us',
    href: 'mailto:team@example.com',
    icon: 'email',
    description: 'Send a direct message to the project team',
  },
]

function validate(): boolean {
  const e: Partial<FormState> = {}
  if (!form.value.name.trim()) e.name = 'Name is required.'
  if (!form.value.email.trim()) {
    e.email = 'Email is required.'
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.value.email)) {
    e.email = 'Please enter a valid email address.'
  }
  if (!form.value.message.trim()) e.message = 'Message is required.'
  errors.value = e
  return Object.keys(e).length === 0
}

function handleSubmit() {
  if (!validate()) return
  // In a real deployment this would call an API endpoint.
  submitted.value = true
}

function resetForm() {
  form.value = { name: '', email: '', message: '' }
  errors.value = {}
  submitted.value = false
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-b from-slate-50 to-white">

    <!-- Page hero -->
    <section class="border-b border-slate-100 bg-white/80 py-14 text-center backdrop-blur-sm">
      <span class="inline-block rounded-full bg-teal-100 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-teal-700">Get in Touch</span>
      <h1 class="mt-4 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">Contact Us</h1>
      <p class="mx-auto mt-3 max-w-md text-base text-slate-500">
        Have questions about the project or want to collaborate? Drop us a message below
        or reach out through our social profiles.
      </p>
    </section>

    <div class="mx-auto grid max-w-4xl gap-10 px-4 py-12 sm:px-6 lg:grid-cols-5">

      <!-- Contact form -->
      <section class="lg:col-span-3">
        <h2 class="mb-6 text-lg font-semibold text-slate-800">Send a Message</h2>

        <!-- Success state -->
        <div
          v-if="submitted"
          class="flex flex-col items-center gap-4 rounded-2xl border border-green-200 bg-green-50 px-6 py-10 text-center"
        >
          <svg class="h-12 w-12 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <p class="text-base font-semibold text-green-800">Message received!</p>
          <p class="text-sm text-green-700">Thank you for reaching out. We'll get back to you shortly.</p>
          <button
            class="mt-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-green-600"
            @click="resetForm"
          >
            Send another message
          </button>
        </div>

        <!-- Form -->
        <form
          v-else
          novalidate
          class="flex flex-col gap-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
          @submit.prevent="handleSubmit"
        >
          <!-- Name -->
          <div>
            <label for="contact-name" class="mb-1.5 block text-sm font-medium text-slate-700">Full Name</label>
            <input
              id="contact-name"
              v-model="form.name"
              type="text"
              autocomplete="name"
              placeholder="Chi Lon Thon"
              class="w-full rounded-lg border px-3 py-2 text-sm text-slate-800 placeholder-slate-400 transition focus:outline-none focus:ring-2"
              :class="errors.name
                ? 'border-red-300 focus:ring-red-400'
                : 'border-slate-200 focus:ring-teal-400'"
            />
            <p v-if="errors.name" class="mt-1 text-xs text-red-600" role="alert">{{ errors.name }}</p>
          </div>

          <!-- Email -->
          <div>
            <label for="contact-email" class="mb-1.5 block text-sm font-medium text-slate-700">Email Address</label>
            <input
              id="contact-email"
              v-model="form.email"
              type="email"
              autocomplete="email"
              placeholder="chilonthon@example.com"
              class="w-full rounded-lg border px-3 py-2 text-sm text-slate-800 placeholder-slate-400 transition focus:outline-none focus:ring-2"
              :class="errors.email
                ? 'border-red-300 focus:ring-red-400'
                : 'border-slate-200 focus:ring-teal-400'"
            />
            <p v-if="errors.email" class="mt-1 text-xs text-red-600" role="alert">{{ errors.email }}</p>
          </div>

          <!-- Message -->
          <div>
            <label for="contact-message" class="mb-1.5 block text-sm font-medium text-slate-700">Message</label>
            <textarea
              id="contact-message"
              v-model="form.message"
              rows="5"
              placeholder="Tell us about your question or feedback…"
              class="w-full resize-none rounded-lg border px-3 py-2 text-sm text-slate-800 placeholder-slate-400 transition focus:outline-none focus:ring-2"
              :class="errors.message
                ? 'border-red-300 focus:ring-red-400'
                : 'border-slate-200 focus:ring-teal-400'"
            ></textarea>
            <p v-if="errors.message" class="mt-1 text-xs text-red-600" role="alert">{{ errors.message }}</p>
          </div>

          <button
            type="submit"
            class="w-full rounded-lg bg-teal-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-teal-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700"
          >
            Send Message
          </button>
        </form>
      </section>

      <!-- Links sidebar -->
      <aside class="lg:col-span-2">
        <h2 class="mb-6 text-lg font-semibold text-slate-800">Find Us Online</h2>
        <ul class="flex flex-col gap-3">
          <li v-for="link in links" :key="link.label">
            <a
              :href="link.href"
              target="_blank"
              rel="noopener noreferrer"
              class="flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-teal-300 hover:shadow-md"
            >
              <!-- GitHub icon -->
              <span v-if="link.icon === 'github'" class="mt-0.5 shrink-0 text-slate-700">
                <svg class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clip-rule="evenodd"/></svg>
              </span>
              <!-- LinkedIn icon -->
              <span v-else-if="link.icon === 'linkedin'" class="mt-0.5 shrink-0 text-blue-600">
                <svg class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
              </span>
              <!-- Email icon -->
              <span v-else class="mt-0.5 shrink-0 text-teal-600">
                <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75"/></svg>
              </span>
              <span>
                <span class="block text-sm font-semibold text-slate-800">{{ link.label }}</span>
                <span class="block text-xs text-slate-500">{{ link.description }}</span>
              </span>
            </a>
          </li>
        </ul>

        <!-- Course tag -->
        <div class="mt-6 rounded-2xl border border-slate-100 bg-slate-50 p-4">
          <p class="text-xs text-slate-500 leading-relaxed">
            <strong class="text-slate-700">COS40007 — AI For Engineering<br/></strong>
            Swinburne University of Technology
          </p>
        </div>
      </aside>
    </div>
  </div>
</template>
