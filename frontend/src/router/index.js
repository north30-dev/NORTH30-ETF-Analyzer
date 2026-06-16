import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Home', component: () => import('../views/HomeView.vue') },
  { path: '/etf', name: 'ETF', component: () => import('../views/ETFView.vue') },
  { path: '/analysis', name: 'Analysis', component: () => import('../views/AnalysisView.vue') },
  { path: '/charts', name: 'Charts', component: () => import('../views/ChartsView.vue') },
  { path: '/report', name: 'Report', component: () => import('../views/ReportView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
