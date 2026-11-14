<script setup lang="ts">
import { ref } from 'vue'
import { X } from '@lucide/vue'

const props = withDefaults(
  defineProps<{
    modelValue: string[]
    placeholder?: string
    max?: number
  }>(),
  {
    placeholder: 'Ajouter puis Entrée…',
    max: 20,
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const draft = ref('')

function add(): void {
  const value = draft.value.replace(/,+$/, '').trim()
  if (!value) {
    return
  }
  if (props.modelValue.length >= props.max) {
    return
  }
  if (!props.modelValue.includes(value)) {
    emit('update:modelValue', [...props.modelValue, value])
  }
  draft.value = ''
}

function remove(value: string): void {
  emit(
    'update:modelValue',
    props.modelValue.filter((item) => item !== value),
  )
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' || event.key === ',') {
    event.preventDefault()
    add()
    return
  }
  if (event.key === 'Backspace' && !draft.value && props.modelValue.length > 0) {
    remove(props.modelValue[props.modelValue.length - 1] as string)
  }
}
</script>

<template>
  <div
    class="flex min-h-[46px] flex-wrap items-center gap-1.5 rounded-xl border border-neutral-200 bg-white px-2.5 py-2 shadow-sm transition focus-within:border-neutral-400 focus-within:ring-4 focus-within:ring-neutral-900/5"
  >
    <span
      v-for="item in modelValue"
      :key="item"
      class="inline-flex items-center gap-1 rounded-lg bg-neutral-100 py-1 pl-2 pr-1 text-xs font-medium text-neutral-700"
    >
      {{ item }}
      <button
        type="button"
        class="rounded p-0.5 text-neutral-400 transition-colors hover:bg-neutral-200 hover:text-neutral-700"
        :aria-label="`Retirer ${item}`"
        @click="remove(item)"
      >
        <X :size="12" />
      </button>
    </span>

    <input
      v-model="draft"
      type="text"
      class="min-w-[140px] flex-1 border-0 bg-transparent px-1.5 py-1 text-sm outline-none placeholder:text-neutral-400"
      :placeholder="modelValue.length >= max ? `Maximum ${max} atteint` : placeholder"
      :disabled="modelValue.length >= max"
      @keydown="onKeydown"
      @blur="add"
    />
  </div>
</template>
