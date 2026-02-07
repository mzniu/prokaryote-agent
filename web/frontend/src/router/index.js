import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { title: '仪表盘', icon: 'Odometer' },
  },
  {
    path: '/skill-tree',
    name: 'SkillTree',
    component: () => import('../views/SkillTree.vue'),
    meta: { title: '技能树', icon: 'Share' },
  },
  {
    path: '/evolution-log',
    name: 'EvolutionLog',
    component: () => import('../views/EvolutionLog.vue'),
    meta: { title: '进化日志', icon: 'Document' },
  },
  {
    path: '/evolution-config',
    name: 'EvolutionConfig',
    component: () => import('../views/EvolutionConfig.vue'),
    meta: { title: '进化配置', icon: 'Setting' },
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: () => import('../views/KnowledgeBase.vue'),
    meta: { title: '知识库', icon: 'Reading' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
