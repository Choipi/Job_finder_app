import { createRouter, createWebHistory } from 'vue-router'

import CampaignPage from '@/pages/CampaignPage.vue'
import DashboardPage from '@/pages/DashboardPage.vue'
import LettersPage from '@/pages/LettersPage.vue'
import OffersPage from '@/pages/OffersPage.vue'
import ProfilePage from '@/pages/ProfilePage.vue'
import SettingsPage from '@/pages/SettingsPage.vue'

declare module 'vue-router' {
  interface RouteMeta {
    title: string
    description: string
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: DashboardPage,
      meta: {
        title: 'Tableau de bord',
        description: 'État du socle, configuration et feuille de route.',
      },
    },
    {
      path: '/offres',
      name: 'offers',
      component: OffersPage,
      meta: {
        title: 'Offres',
        description: 'Les opportunités collectées pour ta campagne, triées par pertinence.',
      },
    },
    {
      path: '/lettres',
      name: 'letters',
      component: LettersPage,
      meta: {
        title: 'Lettres',
        description: 'Génère, relis et conserve tes lettres de motivation.',
      },
    },
    {
      path: '/profil',
      name: 'profile',
      component: ProfilePage,
      meta: {
        title: 'Profil',
        description: 'Ton CV, ta lettre type et les informations utilisées par le LLM.',
      },
    },
    {
      path: '/campagne',
      name: 'campaign',
      component: CampaignPage,
      meta: {
        title: 'Campagne',
        description: 'Critères de recherche, sources, durée et fréquence de collecte.',
      },
    },
    {
      path: '/reglages',
      name: 'settings',
      component: SettingsPage,
      meta: {
        title: 'Réglages',
        description: 'Modèles OpenCode Go, état des sources et consommation.',
      },
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

export default router
