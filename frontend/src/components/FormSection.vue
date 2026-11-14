<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <section class="card p-6">
    <div
      class="flex flex-col gap-2 border-b border-neutral-100 pb-4 sm:flex-row sm:items-start sm:justify-between"
    >
      <div>
        <h2 class="text-sm font-semibold tracking-tight">{{ title }}</h2>
        <p v-if="description" class="mt-1 max-w-2xl text-xs leading-5 text-neutral-500">
          {{ description }}
        </p>
      </div>
      <slot name="aside" />
    </div>

    <div class="pt-5">
      <slot />
    </div>
  </section>
</template>
