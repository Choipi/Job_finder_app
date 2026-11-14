<script setup lang="ts">
import type { Component } from 'vue'
import { computed } from 'vue'
import { Briefcase, LayoutDashboard, Settings, Target, UserRound } from '@lucide/vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

interface NavItem {
  to: string
  label: string
  icon: Component
  phase?: string
}

const route = useRoute()

const nav: NavItem[] = [
  { to: '/', label: 'Tableau de bord', icon: LayoutDashboard },
  { to: '/offres', label: 'Offres', icon: Briefcase, phase: '7' },
  { to: '/profil', label: 'Profil', icon: UserRound },
  { to: '/campagne', label: 'Campagne', icon: Target },
  { to: '/reglages', label: 'Réglages', icon: Settings, phase: '3' },
]

const pageTitle = computed(() => route.meta.title)
const pageDescription = computed(() => route.meta.description)
const isActive = (path: string) => route.path === path
</script>

<template>
  <div class="min-h-screen">
    <!-- Desktop sidebar -->
    <aside
      class="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-neutral-200/80 bg-white md:flex"
    >
      <div class="flex items-center gap-3 px-5 py-6">
        <div class="grid h-10 w-10 place-items-center rounded-xl bg-emerald-600 text-white shadow-lift">
          <Briefcase :size="20" :stroke-width="2" />
        </div>
        <div class="leading-tight">
          <p class="text-sm font-semibold tracking-tight">Job Finder</p>
          <p class="text-xs text-neutral-500">Veille &amp; candidatures</p>
        </div>
      </div>

      <nav class="flex-1 space-y-1 px-3 py-2" aria-label="Navigation principale">
        <RouterLink
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="
            isActive(item.to)
              ? 'bg-neutral-100 text-neutral-900'
              : 'text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900'
          "
        >
          <component :is="item.icon" :size="18" :stroke-width="1.9" />
          <span>{{ item.label }}</span>
          <span
            v-if="item.phase"
            class="ml-auto rounded-md bg-neutral-100 px-1.5 py-0.5 text-[10px] font-semibold text-neutral-500"
            :title="`Disponible à la phase ${item.phase}`"
          >
            P{{ item.phase }}
          </span>
        </RouterLink>
      </nav>

      <div class="border-t border-neutral-100 px-5 py-4">
        <p class="flex items-center gap-2 text-xs font-medium text-neutral-600">
          <span class="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          Phase 1 · Socle
        </p>
        <p class="mt-1 text-[11px] text-neutral-400">v0.1.0 · application locale</p>
      </div>
    </aside>

    <div class="md:pl-64">
      <!-- Mobile header -->
      <header class="sticky top-0 z-20 border-b border-neutral-200/80 bg-white/90 backdrop-blur md:hidden">
        <div class="flex items-center gap-2.5 px-4 py-3">
          <div class="grid h-8 w-8 place-items-center rounded-lg bg-emerald-600 text-white">
            <Briefcase :size="16" />
          </div>
          <p class="text-sm font-semibold tracking-tight">Job Finder</p>
        </div>
        <nav class="flex gap-1 overflow-x-auto px-2 pb-2" aria-label="Navigation mobile">
          <RouterLink
            v-for="item in nav"
            :key="item.to"
            :to="item.to"
            class="whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
            :class="
              isActive(item.to)
                ? 'bg-neutral-100 text-neutral-900'
                : 'text-neutral-500 hover:bg-neutral-50 hover:text-neutral-900'
            "
          >
            {{ item.label }}
          </RouterLink>
        </nav>
      </header>

      <main class="mx-auto w-full max-w-6xl px-5 py-8 md:px-10 md:py-12">
        <div class="mb-8 animate-fade-up">
          <h1 class="text-2xl font-semibold tracking-tight text-neutral-900 md:text-[28px]">
            {{ pageTitle }}
          </h1>
          <p class="mt-1.5 max-w-2xl text-sm leading-6 text-neutral-600">
            {{ pageDescription }}
          </p>
        </div>

        <RouterView v-slot="{ Component }">
          <Transition name="fade" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>
