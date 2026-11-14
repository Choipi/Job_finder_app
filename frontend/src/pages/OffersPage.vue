<script setup lang="ts">
import ComingSoon from '@/components/ComingSoon.vue'
</script>

<template>
  <ComingSoon
    phase="7"
    summary="Une fois la collecte et le scoring en place, chaque opportunité apparaîtra sous forme de carte triée par pertinence."
    :items="[
      'Score de 0 à 100 avec justification et points bloquants.',
      'Trois actions par offre : postuler, supprimer, générer une lettre.',
      'Filtres par source, contrat, télétravail, statut et score.',
      'Statuts de suivi : à postuler, postulé, entretien, refusé.',
      'Suppression réversible, avec blacklist des empreintes.',
    ]"
  />
</template>
