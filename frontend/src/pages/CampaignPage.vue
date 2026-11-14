<script setup lang="ts">
import ComingSoon from '@/components/ComingSoon.vue'
</script>

<template>
  <ComingSoon
    phase="2"
    summary="La campagne borne la recherche dans le temps et décide où chercher. Une seule campagne active à la fois."
    :items="[
      'Date de début et de fin, fréquence de scan.',
      'Mots-clés, lieux, rayon, contrats, télétravail.',
      'Sélection des sources actives, avec avertissement sur celles qui sont fragiles.',
      'Choix des modèles de scoring et de rédaction.',
      'Lancement manuel du scan et suivi de la progression.',
    ]"
  />
</template>
