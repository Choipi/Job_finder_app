<script setup lang="ts">
import { computed } from 'vue'

type Tone = 'ok' | 'warn' | 'error' | 'muted'

const props = withDefaults(
  defineProps<{
    tone: Tone
    label: string
    pulse?: boolean
  }>(),
  { pulse: false },
)

const wrapperClass = computed(
  () =>
    ({
      ok: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
      warn: 'bg-amber-50 text-amber-700 ring-amber-600/20',
      error: 'bg-rose-50 text-rose-700 ring-rose-600/20',
      muted: 'bg-neutral-100 text-neutral-600 ring-neutral-500/15',
    })[props.tone],
)

const dotClass = computed(
  () =>
    ({
      ok: 'bg-emerald-500',
      warn: 'bg-amber-500',
      error: 'bg-rose-500',
      muted: 'bg-neutral-400',
    })[props.tone],
)
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset"
    :class="wrapperClass"
  >
    <span class="h-1.5 w-1.5 rounded-full" :class="[dotClass, pulse ? 'animate-pulse' : '']" />
    {{ label }}
  </span>
</template>
