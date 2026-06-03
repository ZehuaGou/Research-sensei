import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
    { path: '/directions/new', name: 'directions', component: () => import('../views/DirectionSearchView.vue') },
    { path: '/learn/:jobId', name: 'learn', component: () => import('../views/LearningWorkspaceView.vue') },
    { path: '/papers/upload', name: 'upload', component: () => import('../views/UploadView.vue') },
    { path: '/settings', name: 'settings', component: () => import('../views/SettingsView.vue') },
  ],
})

export default router
