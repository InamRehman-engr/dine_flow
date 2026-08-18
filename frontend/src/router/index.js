import { createRouter, createWebHistory } from 'vue-router'
import { getWorkspace, useAuth } from '../composables/useAuth'

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
    meta: { auth: true, role: 'manager' },
    children: [
      { path: '', name: 'admin-floor', component: () => import('../components/AdminLayout.vue') },
      { path: 'orders', name: 'admin-orders', component: () => import('../components/LiveOrders.vue') },
      { path: 'menu', name: 'admin-menu', component: () => import('../components/MenuAdmin.vue') },
      { path: 'stations', name: 'admin-stations', component: () => import('../components/StationsAdmin.vue') },
      { path: 'qrs', name: 'admin-qrs', component: () => import('../components/QrManager.vue') },
      { path: 'settings', name: 'admin-settings', component: () => import('../components/SettingsView.vue') },
    ],
  },
  {
    path: '/kitchen',
    name: 'kitchen',
    component: () => import('../views/KitchenShell.vue'),
    meta: { auth: true, role: 'any' },
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
  const { fetchMe, tenant, staff, homePath } = useAuth()
  if (!tenant.value) await fetchMe()

  if (to.meta.auth && !tenant.value) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // Allow login page always so users can switch workspace / account
  // (do not auto-bounce away from /login)
  if (to.meta.guest && to.name === 'register' && tenant.value) {
    return { path: homePath.value }
  }

  if (to.meta.role === 'manager' && staff.value?.role === 'kitchen') {
    return { path: '/kitchen' }
  }

  // Manager chose kitchen workspace → keep them on KDS unless they open admin deliberately
  // (admin routes stay allowed for managers)
  if (to.name === 'kitchen' && staff.value?.role === 'manager') {
    // ok
  }

  // If landing on / after auth, honor workspace
  if (to.path === '/' && tenant.value) {
    return { path: getWorkspace() === 'kitchen' ? '/kitchen' : '/admin' }
  }

  return true
})

export default router
