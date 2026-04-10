<template>
  <div class="app-layout">
    <!-- Sidebar -->
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <div class="logo-icon">
          <svg viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg" width="32" height="32">
            <rect width="36" height="36" rx="10" fill="rgba(255,255,255,0.15)"/>
            <path d="M11 22 L18 9 L20 17 L25 17 L18 29 L16 20 L11 22Z" fill="#FFFFFF"/>
          </svg>
        </div>
        <transition name="fade">
          <div v-if="!sidebarCollapsed" class="logo-text-group">
            <span class="logo-text">NESOM</span>
            <span class="logo-sub">新能源运维</span>
          </div>
        </transition>
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
        >
          <el-icon :size="20"><component :is="item.icon" /></el-icon>
          <transition name="fade">
            <span v-if="!sidebarCollapsed" class="nav-label">{{ item.label }}</span>
          </transition>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <button class="collapse-btn" @click="sidebarCollapsed = !sidebarCollapsed" aria-label="切换侧边栏">
          <el-icon :size="16">
            <DArrowLeft v-if="!sidebarCollapsed" />
            <DArrowRight v-else />
          </el-icon>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <div class="main-wrapper">
      <!-- Header -->
      <header class="app-header">
        <div class="header-left">
          <h1 class="page-title font-heading">{{ currentTitle }}</h1>
        </div>
        <div class="header-right">
          <div class="header-time font-mono">{{ currentTime }}</div>
          <div class="header-divider"></div>
          <!-- Theme Switcher -->
          <el-dropdown @command="handleThemeChange" trigger="click">
            <div class="theme-trigger" role="button" tabindex="0">
              <el-icon :size="18"><Brush /></el-icon>
              <span class="theme-name">{{ themeStore.currentTheme.name }}</span>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  v-for="theme in themeStore.themes"
                  :key="theme.id"
                  :command="theme.id"
                  :class="{ 'is-active-theme': theme.id === themeStore.currentThemeId }"
                >
                  <span class="theme-dot" :style="{ background: theme.colors.colorPrimary }"></span>
                  <span>{{ theme.name }}</span>
                  <span class="theme-mode-badge">{{ theme.mode === 'dark' ? '暗' : '亮' }}</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <div class="header-divider"></div>
          <el-dropdown @command="handleCommand" trigger="click">
            <div class="user-trigger" role="button" tabindex="0">
              <div class="avatar-circle">{{ avatarLetter }}</div>
              <span class="user-name">{{ displayName }}</span>
              <el-icon :size="12" color="#94A3B8"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- Page Content -->
      <main class="page-content">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useThemeStore } from '@/stores/theme'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const themeStore = useThemeStore()

const sidebarCollapsed = ref(false)
const currentTime = ref('')
let timer: ReturnType<typeof setInterval> | null = null

const menuItems = [
  { path: '/', label: '运营总览', icon: 'Odometer' },
  { path: '/devices', label: '设备监控', icon: 'Monitor' },
  { path: '/work-orders', label: '工单管理', icon: 'Document' },
  { path: '/spare-parts', label: '备件管理', icon: 'Box' },
  { path: '/inspections', label: '巡检管理', icon: 'Search' },
  { path: '/reports', label: '报表统计', icon: 'DataAnalysis' },
  { path: '/system', label: '系统配置', icon: 'Setting' },
]

const currentTitle = computed(() => {
  const matched = route.matched.find(r => r.meta?.title)
  return (matched?.meta?.title as string) || '运营总览'
})

const displayName = computed(() =>
  userStore.userInfo?.realName || userStore.userInfo?.username || '用户'
)
const avatarLetter = computed(() => displayName.value.charAt(0).toUpperCase())

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

function updateTime() {
  currentTime.value = new Date().toLocaleString('zh-CN', {
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
  })
}

function handleCommand(cmd: string) {
  if (cmd === 'logout') { userStore.clear(); router.push('/login') }
}

function handleThemeChange(themeId: string) {
  themeStore.setTheme(themeId)
}

onMounted(() => { updateTime(); timer = setInterval(updateTime, 1000) })
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-base);
}

/* ── Sidebar ─────────────────────────────────────────────── */
.sidebar {
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  background: var(--bg-sidebar);
  display: flex;
  flex-direction: column;
  transition: width var(--transition-slow), min-width var(--transition-slow);
  z-index: 20;
  box-shadow: 4px 0 24px rgba(8, 145, 178, 0.12);
}
.sidebar.collapsed {
  width: var(--sidebar-collapsed-width);
  min-width: var(--sidebar-collapsed-width);
}

.sidebar-header {
  height: var(--header-height);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
}
.logo-icon { flex-shrink: 0; display: flex; align-items: center; }
.logo-text-group { display: flex; flex-direction: column; line-height: 1.2; }
.logo-text {
  font-family: var(--font-heading);
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 2px;
}
.logo-sub { font-size: 10px; color: rgba(255,255,255,0.6); letter-spacing: 1px; }

.sidebar-nav {
  flex: 1;
  padding: 16px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 14px;
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  font-size: 14px;
  font-weight: 400;
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
  overflow: hidden;
}
.nav-item:hover {
  background: var(--sidebar-item-hover);
  color: #fff;
}
.nav-item.active {
  background: var(--sidebar-item-active);
  color: #fff;
  font-weight: 600;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.15);
}

.sidebar-footer {
  padding: 12px 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
}
.collapse-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
  border: none;
  background: transparent;
  color: rgba(255,255,255,0.5);
  cursor: pointer;
  border-radius: 8px;
  transition: all var(--transition-fast);
}
.collapse-btn:hover { background: rgba(255,255,255,0.1); color: #fff; }

/* ── Main Wrapper ────────────────────────────────────────── */
.main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

/* ── Header ──────────────────────────────────────────────── */
.app-header {
  height: var(--header-height);
  min-height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  background: var(--header-bg);
  backdrop-filter: var(--glass-blur);
  border-bottom: 1px solid var(--border-light);
  z-index: 10;
}

.page-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-time {
  font-size: 13px;
  color: var(--text-muted);
  letter-spacing: 0.5px;
}

.header-divider {
  width: 1px;
  height: 20px;
  background: var(--border-default);
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 10px;
  border-radius: 10px;
  transition: background var(--transition-fast);
}
.user-trigger:hover { background: var(--bg-hover); }

.theme-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 8px;
  transition: background var(--transition-fast);
  color: var(--text-secondary);
}
.theme-trigger:hover { background: var(--bg-hover); color: var(--color-primary); }
.theme-name { font-size: 12px; font-weight: 500; }

:deep(.is-active-theme) {
  color: var(--color-primary) !important;
  font-weight: 600;
}
:deep(.theme-dot) {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 6px;
  flex-shrink: 0;
}
:deep(.theme-mode-badge) {
  margin-left: auto;
  padding-left: 12px;
  font-size: 11px;
  color: var(--text-muted);
}

.avatar-circle {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, #0891B2, #22D3EE);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  color: #fff;
  font-family: var(--font-heading);
}

.user-name {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

/* ── Page Content ────────────────────────────────────────── */
.page-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
}

/* ── Transitions ─────────────────────────────────────────── */
.fade-enter-active, .fade-leave-active { transition: opacity var(--transition-normal); }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.page-enter-active { transition: opacity var(--transition-normal), transform var(--transition-normal); }
.page-leave-active { transition: opacity var(--transition-fast); }
.page-enter-from { opacity: 0; transform: translateY(6px); }
.page-leave-to { opacity: 0; }
</style>
