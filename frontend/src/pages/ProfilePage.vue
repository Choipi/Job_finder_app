<script setup lang="ts">
import ComingSoon from '@/components/ComingSoon.vue'
</script>

<template>
  <ComingSoon
    phase="2"
    summary="Le profil sert à la fois à juger les offres et à rédiger les lettres. Il reste modifiable à tout moment."
    :items="[
      'Upload du CV en PDF, extraction du texte et correction manuelle.',
      'Lettre type de référence, avec variables remplies automatiquement.',
      'Coordonnées, poste visé et préférences de recherche.',
      'Aperçu exact de ce qui sera envoyé au LLM.',
    ]"
  />
</template>
