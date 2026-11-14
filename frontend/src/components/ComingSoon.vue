<script setup lang="ts">
import { ArrowRight, Compass } from '@lucide/vue'
import { RouterLink } from 'vue-router'

defineProps<{
  phase: string
  summary: string
  items: string[]
}>()
</script>

<template>
  <section class="card overflow-hidden">
    <div class="border-b border-neutral-100 bg-neutral-50/60 px-6 py-5">
      <div class="flex items-center gap-2 text-xs font-medium text-neutral-500">
        <Compass :size="15" />
        <span>Phase {{ phase }}</span>
      </div>
      <p class="mt-2 text-sm leading-6 text-neutral-600">{{ summary }}</p>
    </div>

    <ul class="divide-y divide-neutral-100">
      <li v-for="item in items" :key="item" class="flex items-start gap-3 px-6 py-3.5">
        <span class="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-neutral-300" />
        <span class="text-sm text-neutral-700">{{ item }}</span>
      </li>
    </ul>

    <div class="border-t border-neutral-100 px-6 py-4">
      <RouterLink
        to="/"
        class="inline-flex items-center gap-2 text-sm font-medium text-emerald-700 transition-colors hover:text-emerald-800"
      >
        Retour au tableau de bord
        <ArrowRight :size="15" />
      </RouterLink>
    </div>
  </section>
</template>
