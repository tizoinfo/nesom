<template>
  <div class="login-page">
    <!-- Theme Switcher (floating top-right) -->
    <div class="login-theme-switcher">
      <el-dropdown @command="handleThemeChange" trigger="click">
        <div class="theme-btn" role="button" tabindex="0">
          <el-icon :size="16"><Brush /></el-icon>
          <span>{{ themeStore.currentTheme.name }}</span>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              v-for="theme in themeStore.themes"
              :key="theme.id"
              :command="theme.id"
            >
              <span class="theme-dot" :style="{ background: theme.colors.colorPrimary }"></span>
              <span>{{ theme.name }}</span>
              <span class="theme-badge">{{ theme.mode === 'dark' ? '暗' : '亮' }}</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <!-- Left: Illustration -->
    <div class="login-left">
      <div class="left-content">
        <!-- Decorative SVG illustration: wind turbines + solar panels -->
        <svg class="illustration" viewBox="0 0 480 400" fill="none" xmlns="http://www.w3.org/2000/svg">
          <!-- Sky gradient bg -->
          <defs>
            <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#E0F7FA"/>
              <stop offset="100%" stop-color="#B2EBF2"/>
            </linearGradient>
            <linearGradient id="blade" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#FFFFFF"/>
              <stop offset="100%" stop-color="#E0F2FE"/>
            </linearGradient>
            <linearGradient id="tower" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#CBD5E1"/>
              <stop offset="100%" stop-color="#94A3B8"/>
            </linearGradient>
            <linearGradient id="panel" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stop-color="#0891B2"/>
              <stop offset="100%" stop-color="#0E7490"/>
            </linearGradient>
            <linearGradient id="ground" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#D1FAE5"/>
              <stop offset="100%" stop-color="#A7F3D0"/>
            </linearGradient>
          </defs>
          <!-- Ground -->
          <ellipse cx="240" cy="370" rx="240" ry="40" fill="url(#ground)" opacity="0.6"/>
          <!-- Hills -->
          <path d="M0 340 Q80 280 160 320 Q240 280 320 310 Q400 270 480 320 L480 400 L0 400Z" fill="#A7F3D0" opacity="0.4"/>
          <path d="M0 360 Q120 310 240 340 Q360 310 480 350 L480 400 L0 400Z" fill="#6EE7B7" opacity="0.3"/>

          <!-- Wind Turbine 1 (left) -->
          <rect x="118" y="160" width="4" height="190" rx="2" fill="url(#tower)"/>
          <circle cx="120" cy="160" r="6" fill="#E2E8F0"/>
          <g class="turbine-blades" style="transform-origin: 120px 160px">
            <rect x="117" y="100" width="6" height="60" rx="3" fill="url(#blade)" stroke="#CBD5E1" stroke-width="0.5"/>
            <rect x="117" y="100" width="6" height="60" rx="3" fill="url(#blade)" stroke="#CBD5E1" stroke-width="0.5" transform="rotate(120 120 160)"/>
            <rect x="117" y="100" width="6" height="60" rx="3" fill="url(#blade)" stroke="#CBD5E1" stroke-width="0.5" transform="rotate(240 120 160)"/>
          </g>

          <!-- Wind Turbine 2 (center, taller) -->
          <rect x="228" y="120" width="5" height="230" rx="2.5" fill="url(#tower)"/>
          <circle cx="230.5" cy="120" r="7" fill="#E2E8F0"/>
          <g class="turbine-blades turbine-2" style="transform-origin: 230.5px 120px">
            <rect x="227.5" y="45" width="6" height="75" rx="3" fill="url(#blade)" stroke="#CBD5E1" stroke-width="0.5"/>
            <rect x="227.5" y="45" width="6" height="75" rx="3" fill="url(#blade)" stroke="#CBD5E1" stroke-width="0.5" transform="rotate(120 230.5 120)"/>
            <rect x="227.5" y="45" width="6" height="75" rx="3" fill="url(#blade)" stroke="#CBD5E1" stroke-width="0.5" transform="rotate(240 230.5 120)"/>
          </g>

          <!-- Wind Turbine 3 (right, small) -->
          <rect x="358" y="180" width="4" height="170" rx="2" fill="url(#tower)"/>
          <circle cx="360" cy="180" r="5" fill="#E2E8F0"/>
          <g class="turbine-blades turbine-3" style="transform-origin: 360px 180px">
            <rect x="357.5" y="130" width="5" height="50" rx="2.5" fill="url(#blade)" stroke="#CBD5E1" stroke-width="0.5"/>
            <rect x="357.5" y="130" width="5" height="50" rx="2.5" fill="url(#blade)" stroke="#CBD5E1" stroke-width="0.5" transform="rotate(120 360 180)"/>
            <rect x="357.5" y="130" width="5" height="50" rx="2.5" fill="url(#blade)" stroke="#CBD5E1" stroke-width="0.5" transform="rotate(240 360 180)"/>
          </g>

          <!-- Solar Panels -->
          <g transform="translate(60, 310) rotate(-8)">
            <rect width="60" height="35" rx="2" fill="url(#panel)" opacity="0.9"/>
            <line x1="20" y1="0" x2="20" y2="35" stroke="rgba(255,255,255,0.3)" stroke-width="0.5"/>
            <line x1="40" y1="0" x2="40" y2="35" stroke="rgba(255,255,255,0.3)" stroke-width="0.5"/>
            <line x1="0" y1="12" x2="60" y2="12" stroke="rgba(255,255,255,0.3)" stroke-width="0.5"/>
            <line x1="0" y1="24" x2="60" y2="24" stroke="rgba(255,255,255,0.3)" stroke-width="0.5"/>
          </g>
          <g transform="translate(300, 320) rotate(-5)">
            <rect width="70" height="40" rx="2" fill="url(#panel)" opacity="0.85"/>
            <line x1="23" y1="0" x2="23" y2="40" stroke="rgba(255,255,255,0.3)" stroke-width="0.5"/>
            <line x1="47" y1="0" x2="47" y2="40" stroke="rgba(255,255,255,0.3)" stroke-width="0.5"/>
            <line x1="0" y1="13" x2="70" y2="13" stroke="rgba(255,255,255,0.3)" stroke-width="0.5"/>
            <line x1="0" y1="27" x2="70" y2="27" stroke="rgba(255,255,255,0.3)" stroke-width="0.5"/>
          </g>

          <!-- Sun -->
          <circle cx="400" cy="60" r="30" fill="#FBBF24" opacity="0.3"/>
          <circle cx="400" cy="60" r="18" fill="#FCD34D" opacity="0.5"/>

          <!-- Clouds -->
          <g opacity="0.4">
            <ellipse cx="80" cy="70" rx="30" ry="12" fill="white"/>
            <ellipse cx="100" cy="65" rx="20" ry="10" fill="white"/>
          </g>
          <g opacity="0.3">
            <ellipse cx="300" cy="50" rx="25" ry="10" fill="white"/>
            <ellipse cx="320" cy="46" rx="18" ry="8" fill="white"/>
          </g>
        </svg>

        <div class="left-text">
          <h2 class="font-heading">新能源场站运维管理系统</h2>
          <p>智能监控 · 高效运维 · 数据驱动</p>
        </div>
      </div>
    </div>

    <!-- Right: Login Form -->
    <div class="login-right">
      <div class="login-form-wrapper">
        <div class="form-header">
          <div class="form-logo">
            <svg viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg" width="40" height="40">
              <rect width="36" height="36" rx="10" fill="#0891B2"/>
              <path d="M11 22 L18 9 L20 17 L25 17 L18 29 L16 20 L11 22Z" fill="#FFFFFF"/>
            </svg>
          </div>
          <h1 class="form-title font-heading">欢迎登录</h1>
          <p class="form-subtitle">NESOM 新能源场站运维管理平台</p>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="0"
          @submit.prevent="handleLogin"
        >
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              placeholder="请输入用户名"
              prefix-icon="User"
              size="large"
              :disabled="loading || lockRemaining > 0"
              @keyup.enter="focusPassword"
            />
          </el-form-item>

          <el-form-item prop="password">
            <el-input
              ref="passwordRef"
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              prefix-icon="Lock"
              show-password
              size="large"
              :disabled="loading || lockRemaining > 0"
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <el-alert
            v-if="lockRemaining > 0"
            type="warning"
            :title="`账户已锁定，请等待 ${formatLockTime(lockRemaining)} 后重试`"
            show-icon :closable="false" style="margin-bottom: 16px"
          />
          <el-alert
            v-else-if="errorMsg"
            type="error" :title="errorMsg"
            show-icon closable style="margin-bottom: 16px"
            @close="errorMsg = ''"
          />

          <el-form-item>
            <el-button
              type="primary"
              native-type="submit"
              :loading="loading"
              :disabled="lockRemaining > 0"
              size="large"
              class="login-btn"
              @click="handleLogin"
            >
              {{ lockRemaining > 0 ? `锁定中 (${formatLockTime(lockRemaining)})` : '登 录' }}
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useThemeStore } from '@/stores/theme'
import request from '@/utils/request'
import type { UserInfo } from '@/types/user'

interface LoginResponse {
  access_token: string; refresh_token: string; token_type: string; expires_in: number; user: UserInfo
}

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const themeStore = useThemeStore()

const formRef = ref<FormInstance>()
const passwordRef = ref()
const loading = ref(false)
const errorMsg = ref('')
const lockRemaining = ref(0)
const form = ref({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

let lockTimer: ReturnType<typeof setInterval> | null = null

function startLockCountdown(seconds: number) {
  lockRemaining.value = seconds
  if (lockTimer) clearInterval(lockTimer)
  lockTimer = setInterval(() => {
    lockRemaining.value -= 1
    if (lockRemaining.value <= 0) { lockRemaining.value = 0; if (lockTimer) clearInterval(lockTimer) }
  }, 1000)
}

function formatLockTime(seconds: number): string {
  const m = Math.floor(seconds / 60); const s = seconds % 60
  return m > 0 ? `${m}分${s}秒` : `${s}秒`
}

function focusPassword() { passwordRef.value?.focus() }

async function handleLogin() {
  if (lockRemaining.value > 0) return
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true; errorMsg.value = ''
  try {
    const data = await request.post<any, LoginResponse>('/v1/auth/login', {
      username: form.value.username, password: form.value.password,
    })
    userStore.setToken(data.access_token, data.refresh_token)
    if (data.user) userStore.setUserInfo(data.user)
    ElMessage.success('登录成功')
    router.push((route.query.redirect as string) || '/')
  } catch (err: any) {
    const detail = err?.response?.data
    const code = detail?.code || detail?.detail?.code
    if (code === 'ACCOUNT_LOCKED' || err?.response?.status === 423) {
      startLockCountdown(detail?.detail?.lockout_remaining ?? 1800)
    } else {
      errorMsg.value = detail?.message || detail?.detail || '用户名或密码错误'
    }
  } finally { loading.value = false }
}

function handleThemeChange(themeId: string) {
  themeStore.setTheme(themeId)
}

onUnmounted(() => { if (lockTimer) clearInterval(lockTimer) })
</script>

<style scoped>
.login-page {
  display: flex;
  min-height: 100vh;
  background: var(--bg-base);
  position: relative;
}

.login-theme-switcher {
  position: absolute;
  top: 16px;
  right: 20px;
  z-index: 100;
}
.theme-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 10px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}
.theme-btn:hover {
  border-color: var(--color-primary-light);
  color: var(--color-primary);
  box-shadow: var(--shadow-md);
}
:deep(.theme-dot) {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 4px;
  flex-shrink: 0;
}
:deep(.theme-badge) {
  margin-left: auto;
  padding-left: 12px;
  font-size: 11px;
  color: var(--text-muted);
}

/* ── Left Panel ──────────────────────────────────────────── */
.login-left {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #ECFEFF 0%, #CFFAFE 50%, #A5F3FC 100%);
  position: relative;
  overflow: hidden;
  padding: 40px;
}

.left-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
  max-width: 500px;
}

.illustration {
  width: 100%;
  max-width: 440px;
  height: auto;
}

/* Turbine blade rotation */
@keyframes spin-slow {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.turbine-blades { animation: spin-slow 8s linear infinite; }
.turbine-2 { animation: spin-slow 6s linear infinite; }
.turbine-3 { animation: spin-slow 10s linear infinite; }

@media (prefers-reduced-motion: reduce) {
  .turbine-blades, .turbine-2, .turbine-3 { animation: none; }
}

.left-text {
  text-align: center;
}
.left-text h2 {
  font-size: 22px;
  font-weight: 700;
  color: #0E7490;
  margin-bottom: 8px;
}
.left-text p {
  font-size: 14px;
  color: #0891B2;
  letter-spacing: 3px;
}

/* ── Right Panel ─────────────────────────────────────────── */
.login-right {
  width: 460px;
  min-width: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: var(--bg-surface);
  box-shadow: -8px 0 40px rgba(8, 145, 178, 0.06);
}

.login-form-wrapper {
  width: 100%;
  max-width: 360px;
}

.form-header {
  text-align: center;
  margin-bottom: 36px;
}
.form-logo {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
}
.form-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px;
}
.form-subtitle {
  font-size: 13px;
  color: var(--text-muted);
}

.login-btn {
  width: 100%;
  height: 46px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 6px;
  border-radius: 10px;
}

/* ── Responsive ──────────────────────────────────────────── */
@media (max-width: 900px) {
  .login-left { display: none; }
  .login-right { width: 100%; min-width: unset; }
}
</style>
