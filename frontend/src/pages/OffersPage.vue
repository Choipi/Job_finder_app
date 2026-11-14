<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  AlertCircle,
  Briefcase,
  Building2,
  ExternalLink,
  LoaderCircle,
  RefreshCw,
  Search,
} from '@lucide/vue'
import { RouterLink } from 'vue-router'

import type { OfferSummary } from '@/api/types'
import { useOffersStore } from '@/stores/offers'

const store = useOffersStore()
const search = ref('')
const remote = ref('')
const filterByCampaign = ref(true)

const REMOTE_LABELS: Record<string, string> = {
  remote: 'Télétravail',
  hybrid: 'Hybride',
  onsite: 'Sur site',
}

onMounted(async () => {
  try {
    await store.load({ limit: 200, campaign: true })
  } catch {
    // Store error is displayed above.
  }
})

async function reload(): Promise<void> {
  try {
    await store.load({
      q: search.value,
      remote: remote.value,
      limit: 200,
      campaign: filterByCampaign.value,
    })
  } catch {
    // Store error is displayed above.
  }
}

function formatDate(value: string | null): string {
  if (!value) {
    return '—'
  }
  return new Date(value).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

function applyLink(offer: OfferSummary): string {
  return offer.apply_url || '#'
}
</script>

<template>
  <div class="space-y-6">
    <Transition name="fade">
      <div
        v-if="store.error"
        class="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800"
      >
        <AlertCircle :size="16" class="mt-0.5 shrink-0" />
        <p>{{ store.error }}</p>
      </div>
    </Transition>

    <section class="card p-6">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 class="text-sm font-semibold tracking-tight">Offres collectées</h2>
          <p class="mt-1 text-xs leading-5 text-neutral-500">
            {{ store.total }} offre(s) en base, issues des ATS de la watchlist. Le scoring et le
            suivi de candidature arrivent dans les prochaines phases.
          </p>
        </div>

        <form class="flex flex-col gap-2 sm:flex-row sm:items-center" @submit.prevent="reload">
          <div class="relative">
            <Search :size="14" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400" />
            <input
              v-model="search"
              class="input py-2 pl-9 text-xs"
              type="search"
              placeholder="Titre de l’offre…"
            />
          </div>
          <select v-model="remote" class="select py-2 text-xs">
            <option value="">Tous les modes</option>
            <option value="remote">Télétravail</option>
            <option value="hybrid">Hybride</option>
            <option value="onsite">Sur site</option>
          </select>
          <button type="submit" class="btn-ghost px-3 py-2" :disabled="store.loading">
            <LoaderCircle v-if="store.loading" :size="14" class="animate-spin" />
            <RefreshCw v-else :size="14" />
            Filtrer
          </button>
        </form>
      </div>

      <div class="mt-4 flex flex-col gap-2 border-t border-neutral-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
        <label class="inline-flex cursor-pointer items-center gap-2 text-xs text-neutral-600">
          <input
            v-model="filterByCampaign"
            type="checkbox"
            class="h-4 w-4 accent-emerald-600"
            @change="reload"
          />
          Filtrer selon ma campagne (mots-clés, lieux, télétravail)
        </label>
        <p v-if="store.campaignFilter?.active" class="text-[11px] text-neutral-400">
          <template v-if="store.campaignFilter.keywords.length > 0">
            Mots-clés : {{ store.campaignFilter.keywords.join(', ') }}
          </template>
          <template v-else>Aucun mot-clé dans la campagne.</template>
          <template v-if="store.campaignFilter.locations.length > 0">
            · Lieux : {{ store.campaignFilter.locations.join(', ') }}
          </template>
        </p>
      </div>
    </section>

    <div v-if="store.offers.length > 0" class="grid gap-4 lg:grid-cols-2">
      <article v-for="offer in store.offers" :key="offer.id" class="card flex flex-col p-5">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h3 class="text-sm font-semibold leading-5 tracking-tight text-neutral-900">
              {{ offer.title }}
            </h3>
            <p class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-neutral-500">
              <span class="inline-flex items-center gap-1">
                <Building2 :size="12" />
                {{ offer.company || 'Entreprise non précisée' }}
              </span>
              <span v-if="offer.location">· {{ offer.location }}</span>
            </p>
          </div>
          <span
            v-if="offer.remote"
            class="shrink-0 rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20"
          >
            {{ REMOTE_LABELS[offer.remote] ?? offer.remote }}
          </span>
        </div>

        <div class="mt-3 flex flex-wrap items-center gap-1.5 text-[10px] text-neutral-500">
          <span v-if="offer.contract_type" class="rounded-md bg-neutral-100 px-1.5 py-0.5">
            {{ offer.contract_type }}
          </span>
          <span class="rounded-md bg-neutral-100 px-1.5 py-0.5">ATS employeur</span>
          <span class="rounded-md bg-neutral-100 px-1.5 py-0.5">
            Publiée le {{ formatDate(offer.published_at) }}
          </span>
        </div>

        <div class="mt-auto flex items-center justify-between border-t border-neutral-100 pt-4">
          <p class="text-[11px] text-neutral-400">Score et lettre : phases suivantes</p>
          <a
            v-if="offer.apply_url"
            :href="applyLink(offer)"
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex items-center gap-1.5 rounded-lg bg-neutral-900 px-3 py-1.5 text-[11px] font-medium text-white transition-colors hover:bg-neutral-800"
          >
            Postuler
            <ExternalLink :size="12" />
          </a>
          <span v-else class="text-[11px] text-neutral-400">Lien indisponible</span>
        </div>
      </article>
    </div>

    <section v-else class="card flex flex-col items-center justify-center px-6 py-16 text-center">
      <div class="grid h-11 w-11 place-items-center rounded-xl bg-neutral-100 text-neutral-400">
        <Briefcase :size="20" />
      </div>
      <p class="mt-3 text-sm font-medium text-neutral-700">Aucune offre pour l’instant</p>
      <p class="mt-1 max-w-md text-xs leading-5 text-neutral-500">
        Charge la watchlist, détecte les ATS de quelques employeurs, puis lance une collecte.
      </p>
      <RouterLink to="/employeurs" class="btn-primary mt-4">
        Gérer les employeurs
      </RouterLink>
    </section>
  </div>
</template>
