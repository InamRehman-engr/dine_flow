import { createRouter, createWebHistory } from 'vue-router'
import { api } from '../api'
import { getLoginMode, homePathForMode } from '../composables/useLoginMode'

const routes = [
  { path: '/', redirect: '/login' },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { guest: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('../views/RegisterView.vue'),
    meta: { guest: true },
  },
  {
    path: '/forgot-password',
    name: 'forgot',
    component: () => import('../views/ForgotPasswordView.vue'),
    meta: { guest: true },
  },
  {
    path: '/reset-password',
    name: 'reset',
    component: () => import('../views/ResetPasswordView.vue'),
    meta: { guest: true },
  },
  {
    path: '/admin',
    component: () => import('../views/AdminShell.vue'),
    meta: { auth: true, mode: 'admin' },
    children: [
      { path: '', name: 'admin-floor', component: () => import('../components/AdminLayout.vue') },
      { path: 'menu', name: 'admin-menu', component: () => import('../components/MenuAdmin.vue') },
    ],
  },
  {
    path: '/kitchen',
    name: 'kitchen',
    component: () => import('../views/KitchenShell.vue'),
    meta: { auth: true, mode: 'kitchen' },
  },
  {
    path: '/admin/kitchen',
    redirect: '/kitchen',
  },
  {
    path: '/menu',
    name: 'customer-menu',
    component: () => import('../components/CustomerMenu.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  if (!to.meta.auth && !to.meta.guest) return true
  let tenant = null
  try {
    const data = await api.get('/api/auth/me')
    tenant = data.tenant
  } catch {
    tenant = null
  }
  if (to.meta.auth && !tenant) return { name: 'login', query: { redirect: to.fullPath } }
  if (to.meta.guest && tenant && (to.name === 'login' || to.name === 'register')) {
    return { path: homePathForMode() }
  }
  // Soft nudge: if user signed in as kitchen but opens admin routes, keep them on kitchen
  if (to.meta.mode === 'admin' && getLoginMode() === 'kitchen' && to.path.startsWith('/admin')) {
    return { path: '/kitchen' }
  }
  if (to.meta.mode === 'kitchen' && getLoginMode() === 'admin' && to.path === '/kitchen') {
    return { path: '/admin' }
  }
  return true
})

export default router
