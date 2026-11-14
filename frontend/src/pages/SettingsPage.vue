<script setup lang="ts">
import ComingSoon from '@/components/ComingSoon.vue'
</script>

<template>
  <ComingSoon
    phase="3"
    summary="Les réglages exposent la configuration utile sans jamais renvoyer la clé API au navigateur."
    :items="[
      'Sélection des modèles OpenCode Go pour le scoring et les lettres.',
      'État de la clé, configurée ou non, sans jamais l’afficher.',
      'Santé des sources et désactivation en un clic.',
      'Consommation LLM : appels, tokens et coût estimé.',
    ]"
  />
</template>
