import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw, RouteMeta } from 'vue-router'
import { ElMessage } from 'element-plus'

// Extend RouteMeta to support permission-based guards
declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    title?: string
    /** Single permission code required to access this route */
    permission?: string
    /** Multiple permission codes – user must have at least one */
    permissions?: string[]
    /** Require ALL listed permissions (default: any one is enough) */
    requireAllPermissions?: boolean
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: () => import('@/views/error/ForbiddenView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('@/views/layout/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
        meta: { title: '仪表盘' },
      },
      {
        path: 'devices',
        name: 'Devices',
        component: () => import('@/views/device/DeviceListView.vue'),
        meta: { title: '设备监控', permission: 'device:read' },
      },
      {
        path: 'devices/:id',
        name: 'DeviceDetail',
        component: () => import('@/views/device/DeviceDetailView.vue'),
        meta: { title: '设备详情', permission: 'device:read' },
      },
      {
        path: 'devices/:id/alerts',
        name: 'DeviceAlerts',
        component: () => import('@/views/device/DeviceDetailView.vue'),
        meta: { title: '设备告警', permission: 'device:read' },
      },
      {
        path: 'work-orders',
        name: 'WorkOrders',
        component: () => import('@/views/workorder/WorkOrderListView.vue'),
        meta: { title: '工单管理', permission: 'workorder:read' },
      },
      {
        path: 'workorders/:id',
        name: 'WorkOrderDetail',
        component: () => import('@/views/workorder/WorkOrderDetailView.vue'),
        meta: { title: '工单详情', permission: 'workorder:read' },
      },
      {
        path: 'spare-parts',
        name: 'SpareParts',
        component: () => import('@/views/sparepart/SparePartListView.vue'),
        meta: { title: '备件管理', permission: 'sparepart:read' },
      },
      {
        path: 'inspections',
        name: 'Inspections',
        component: () => import('@/views/inspection/InspectionListView.vue'),
        meta: { title: '巡检管理', permission: 'inspection:read' },
      },
      {
        path: 'inspection/plans/:id',
        name: 'InspectionPlanDetail',
        component: () => import('@/views/inspection/InspectionPlanDetailView.vue'),
        meta: { title: '巡检计划详情', permission: 'inspection:read' },
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('@/views/report/ReportView.vue'),
        meta: { title: '报表统计', permission: 'report:read' },
      },
      {
        path: 'system',
        name: 'System',
        component: () => import('@/views/system/SystemConfigView.vue'),
        meta: { title: '系统配置', permission: 'system:config' },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

/** Read token directly from persisted storage to avoid circular Pinia import */
function getStoredToken(): string {
  try {
    const stored = localStorage.getItem('nesom-user')
    return stored ? (JSON.parse(stored).token ?? '') : ''
  } catch {
    return ''
  }
}

/** Read permissions from persisted user info */
function getStoredPermissions(): string[] {
  try {
    const stored = localStorage.getItem('nesom-user')
    return stored ? (JSON.parse(stored).userInfo?.permissions ?? []) : []
  } catch {
    return []
  }
}

/** Check if user is superadmin */
function isSuperAdmin(): boolean {
  try {
    const stored = localStorage.getItem('nesom-user')
    return stored ? (JSON.parse(stored).userInfo?.is_superadmin === true) : false
  } catch {
    return false
  }
}

router.beforeEach((to, _from, next) => {
  const token = getStoredToken()
  const requiresAuth = to.matched.some((r) => r.meta.requiresAuth !== false)

  // 1. Unauthenticated → redirect to login
  if (requiresAuth && !token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }

  // 2. Already logged in → skip login page
  if (to.name === 'Login' && token) {
    next({ name: 'Dashboard' })
    return
  }

  // 3. Permission check (only for authenticated routes, skip for superadmin)
  if (token && requiresAuth && !isSuperAdmin()) {
    const userPermissions = getStoredPermissions()

    // Collect required permissions from the matched route chain
    const requiredPermission = to.meta.permission
    const requiredPermissions = to.meta.permissions ?? []
    const requireAll = to.meta.requireAllPermissions ?? false

    // Single permission shorthand
    if (requiredPermission && !userPermissions.includes(requiredPermission)) {
      ElMessage.error('权限不足，无法访问该页面')
      next({ name: 'Forbidden' })
      return
    }

    // Multiple permissions
    if (requiredPermissions.length > 0) {
      const allowed = requireAll
        ? requiredPermissions.every((p) => userPermissions.includes(p))
        : requiredPermissions.some((p) => userPermissions.includes(p))

      if (!allowed) {
        ElMessage.error('权限不足，无法访问该页面')
        next({ name: 'Forbidden' })
        return
      }
    }
  }

  next()
})

export default router
