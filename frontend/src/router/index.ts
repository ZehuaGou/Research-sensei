import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/directions/new' },
    { path: '/directions/new', name: 'directions', component: () => import('../views/DirectionSearchView.vue') },
    { path: '/papers/library', name: 'paper-library', component: () => import('../views/LibraryView.vue') },
    { path: '/learn/:jobId', name: 'learn', component: () => import('../views/LearningWorkspaceView.vue') },
    { path: '/papers/upload', name: 'upload', component: () => import('../views/UploadView.vue') },
    { path: '/settings', name: 'settings', component: () => import('../views/SettingsView.vue') },
  ],
})

export default router
