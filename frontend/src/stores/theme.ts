import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export interface ThemeConfig {
  id: string
  name: string
  mode: 'light' | 'dark'
  colors: {
    bgBase: string
    bgSurface: string
    bgElevated: string
    bgHover: string
    bgInput: string
    sidebarGradient: string
    borderDefault: string
    borderLight: string
    textPrimary: string
    textSecondary: string
    textMuted: string
    colorPrimary: string
    colorPrimaryLight: string
    colorPrimaryBg: string
    colorSuccess: string
    colorWarning: string
    colorDanger: string
    shadowColor: string
    headerBg: string
    loadingBg: string
    tableStripeBg: string
    tableHoverBg: string
    tableHeaderBg: string
    descLabelBg: string
    scrollbarThumb: string
    tagWarningText: string
  }
}

export const THEMES: ThemeConfig[] = [
  {
    id: 'cyan-tech',
    name: '科技青',
    mode: 'light',
    colors: {
      bgBase: '#F0FDFA',
      bgSurface: '#FFFFFF',
      bgElevated: '#F8FFFE',
      bgHover: '#E0F7FA',
      bgInput: '#FFFFFF',
      sidebarGradient: 'linear-gradient(180deg, #0E7490 0%, #0891B2 40%, #06B6D4 100%)',
      borderDefault: '#B2EBF2',
      borderLight: '#E0F7FA',
      textPrimary: '#0C4A6E',
      textSecondary: '#475569',
      textMuted: '#94A3B8',
      colorPrimary: '#0891B2',
      colorPrimaryLight: '#22D3EE',
      colorPrimaryBg: 'rgba(8,145,178,0.08)',
      colorSuccess: '#10B981',
      colorWarning: '#F59E0B',
      colorDanger: '#EF4444',
      shadowColor: 'rgba(8,145,178,0.06)',
      headerBg: 'rgba(255,255,255,0.75)',
      loadingBg: 'rgba(240,253,250,0.7)',
      tableStripeBg: 'rgba(240,253,250,0.5)',
      tableHoverBg: 'rgba(8,145,178,0.04)',
      tableHeaderBg: '#F0FDFA',
      descLabelBg: '#F0FDFA',
      scrollbarThumb: '#B2EBF2',
      tagWarningText: '#B45309',
    },
  },
  {
    id: 'deep-blue',
    name: '深空蓝',
    mode: 'dark',
    colors: {
      bgBase: '#0B1120',
      bgSurface: '#111827',
      bgElevated: '#1F2937',
      bgHover: '#374151',
      bgInput: '#1F2937',
      sidebarGradient: 'linear-gradient(180deg, #0F172A 0%, #1E3A5F 100%)',
      borderDefault: '#1F2937',
      borderLight: '#1F2937',
      textPrimary: '#F1F5F9',
      textSecondary: '#94A3B8',
      textMuted: '#64748B',
      colorPrimary: '#3B82F6',
      colorPrimaryLight: '#60A5FA',
      colorPrimaryBg: 'rgba(59,130,246,0.1)',
      colorSuccess: '#22C55E',
      colorWarning: '#FBBF24',
      colorDanger: '#EF4444',
      shadowColor: 'rgba(0,0,0,0.3)',
      headerBg: 'rgba(17,24,39,0.85)',
      loadingBg: 'rgba(11,17,32,0.7)',
      tableStripeBg: 'rgba(31,41,55,0.5)',
      tableHoverBg: 'rgba(59,130,246,0.06)',
      tableHeaderBg: '#1F2937',
      descLabelBg: '#1F2937',
      scrollbarThumb: '#374151',
      tagWarningText: '#FBBF24',
    },
  },
  {
    id: 'emerald-green',
    name: '翡翠绿',
    mode: 'light',
    colors: {
      bgBase: '#ECFDF5',
      bgSurface: '#FFFFFF',
      bgElevated: '#F0FDF4',
      bgHover: '#D1FAE5',
      bgInput: '#FFFFFF',
      sidebarGradient: 'linear-gradient(180deg, #065F46 0%, #059669 40%, #10B981 100%)',
      borderDefault: '#A7F3D0',
      borderLight: '#D1FAE5',
      textPrimary: '#064E3B',
      textSecondary: '#475569',
      textMuted: '#94A3B8',
      colorPrimary: '#059669',
      colorPrimaryLight: '#34D399',
      colorPrimaryBg: 'rgba(5,150,105,0.08)',
      colorSuccess: '#0891B2',
      colorWarning: '#F59E0B',
      colorDanger: '#EF4444',
      shadowColor: 'rgba(5,150,105,0.06)',
      headerBg: 'rgba(255,255,255,0.75)',
      loadingBg: 'rgba(236,253,245,0.7)',
      tableStripeBg: 'rgba(236,253,245,0.5)',
      tableHoverBg: 'rgba(5,150,105,0.04)',
      tableHeaderBg: '#ECFDF5',
      descLabelBg: '#ECFDF5',
      scrollbarThumb: '#A7F3D0',
      tagWarningText: '#B45309',
    },
  },
  {
    id: 'indigo-purple',
    name: '靛蓝紫',
    mode: 'light',
    colors: {
      bgBase: '#F5F3FF',
      bgSurface: '#FFFFFF',
      bgElevated: '#FAF5FF',
      bgHover: '#EDE9FE',
      bgInput: '#FFFFFF',
      sidebarGradient: 'linear-gradient(180deg, #3730A3 0%, #4F46E5 40%, #6366F1 100%)',
      borderDefault: '#C4B5FD',
      borderLight: '#EDE9FE',
      textPrimary: '#1E1B4B',
      textSecondary: '#475569',
      textMuted: '#94A3B8',
      colorPrimary: '#6366F1',
      colorPrimaryLight: '#818CF8',
      colorPrimaryBg: 'rgba(99,102,241,0.08)',
      colorSuccess: '#10B981',
      colorWarning: '#F59E0B',
      colorDanger: '#EF4444',
      shadowColor: 'rgba(99,102,241,0.06)',
      headerBg: 'rgba(255,255,255,0.75)',
      loadingBg: 'rgba(245,243,255,0.7)',
      tableStripeBg: 'rgba(245,243,255,0.5)',
      tableHoverBg: 'rgba(99,102,241,0.04)',
      tableHeaderBg: '#F5F3FF',
      descLabelBg: '#F5F3FF',
      scrollbarThumb: '#C4B5FD',
      tagWarningText: '#B45309',
    },
  },
  {
    id: 'amber-orange',
    name: '琥珀橙',
    mode: 'light',
    colors: {
      bgBase: '#FFFBEB',
      bgSurface: '#FFFFFF',
      bgElevated: '#FEF9EE',
      bgHover: '#FEF3C7',
      bgInput: '#FFFFFF',
      sidebarGradient: 'linear-gradient(180deg, #92400E 0%, #B45309 40%, #D97706 100%)',
      borderDefault: '#FDE68A',
      borderLight: '#FEF3C7',
      textPrimary: '#78350F',
      textSecondary: '#57534E',
      textMuted: '#A8A29E',
      colorPrimary: '#D97706',
      colorPrimaryLight: '#F59E0B',
      colorPrimaryBg: 'rgba(217,119,6,0.08)',
      colorSuccess: '#10B981',
      colorWarning: '#EA580C',
      colorDanger: '#EF4444',
      shadowColor: 'rgba(217,119,6,0.06)',
      headerBg: 'rgba(255,255,255,0.75)',
      loadingBg: 'rgba(255,251,235,0.7)',
      tableStripeBg: 'rgba(255,251,235,0.5)',
      tableHoverBg: 'rgba(217,119,6,0.04)',
      tableHeaderBg: '#FFFBEB',
      descLabelBg: '#FFFBEB',
      scrollbarThumb: '#FDE68A',
      tagWarningText: '#C2410C',
    },
  },
  {
    id: 'graphite-gray',
    name: '石墨灰',
    mode: 'dark',
    colors: {
      bgBase: '#18181B',
      bgSurface: '#27272A',
      bgElevated: '#3F3F46',
      bgHover: '#52525B',
      bgInput: '#27272A',
      sidebarGradient: 'linear-gradient(180deg, #18181B 0%, #27272A 50%, #3F3F46 100%)',
      borderDefault: '#3F3F46',
      borderLight: '#3F3F46',
      textPrimary: '#FAFAFA',
      textSecondary: '#A1A1AA',
      textMuted: '#71717A',
      colorPrimary: '#A1A1AA',
      colorPrimaryLight: '#D4D4D8',
      colorPrimaryBg: 'rgba(161,161,170,0.1)',
      colorSuccess: '#22C55E',
      colorWarning: '#FBBF24',
      colorDanger: '#EF4444',
      shadowColor: 'rgba(0,0,0,0.4)',
      headerBg: 'rgba(39,39,42,0.85)',
      loadingBg: 'rgba(24,24,27,0.7)',
      tableStripeBg: 'rgba(63,63,70,0.3)',
      tableHoverBg: 'rgba(161,161,170,0.06)',
      tableHeaderBg: '#3F3F46',
      descLabelBg: '#3F3F46',
      scrollbarThumb: '#52525B',
      tagWarningText: '#FBBF24',
    },
  },
]

export const useThemeStore = defineStore('nesom-theme', () => {
  const currentThemeId = ref<string>(localStorage.getItem('nesom-theme') || 'cyan-tech')

  const currentTheme = ref<ThemeConfig>(
    THEMES.find(t => t.id === currentThemeId.value) || THEMES[0]
  )

  function applyTheme(theme: ThemeConfig) {
    const root = document.documentElement
    const c = theme.colors

    // Set CSS variables
    root.style.setProperty('--bg-base', c.bgBase)
    root.style.setProperty('--bg-surface', c.bgSurface)
    root.style.setProperty('--bg-elevated', c.bgElevated)
    root.style.setProperty('--bg-hover', c.bgHover)
    root.style.setProperty('--bg-input', c.bgInput)
    root.style.setProperty('--bg-sidebar', c.sidebarGradient)
    root.style.setProperty('--border-default', c.borderDefault)
    root.style.setProperty('--border-light', c.borderLight)
    root.style.setProperty('--text-primary', c.textPrimary)
    root.style.setProperty('--text-secondary', c.textSecondary)
    root.style.setProperty('--text-muted', c.textMuted)
    root.style.setProperty('--color-primary', c.colorPrimary)
    root.style.setProperty('--color-primary-light', c.colorPrimaryLight)
    root.style.setProperty('--color-primary-bg', c.colorPrimaryBg)
    root.style.setProperty('--color-success', c.colorSuccess)
    root.style.setProperty('--color-warning', c.colorWarning)
    root.style.setProperty('--color-danger', c.colorDanger)
    root.style.setProperty('--shadow-sm', `0 1px 3px ${c.shadowColor}`)
    root.style.setProperty('--shadow-md', `0 4px 16px ${c.shadowColor}`)
    root.style.setProperty('--shadow-lg', `0 8px 32px ${c.shadowColor}`)
    root.style.setProperty('--shadow-card', `0 2px 12px ${c.shadowColor}`)
    root.style.setProperty('--shadow-glow', `0 0 24px ${c.colorPrimaryBg}`)
    root.style.setProperty('--header-bg', c.headerBg)
    root.style.setProperty('--loading-bg', c.loadingBg)
    root.style.setProperty('--table-stripe-bg', c.tableStripeBg)
    root.style.setProperty('--table-hover-bg', c.tableHoverBg)
    root.style.setProperty('--table-header-bg', c.tableHeaderBg)
    root.style.setProperty('--desc-label-bg', c.descLabelBg)
    root.style.setProperty('--scrollbar-thumb', c.scrollbarThumb)
    root.style.setProperty('--tag-warning-text', c.tagWarningText)

    // Sidebar text colors for dark sidebars
    root.style.setProperty('--sidebar-text', 'rgba(255,255,255,0.7)')
    root.style.setProperty('--sidebar-text-active', '#FFFFFF')
    root.style.setProperty('--sidebar-item-hover', 'rgba(255,255,255,0.12)')
    root.style.setProperty('--sidebar-item-active', 'rgba(255,255,255,0.2)')

    // Dark mode specific overrides
    if (theme.mode === 'dark') {
      root.style.setProperty('--el-bg-color', c.bgSurface)
      root.style.setProperty('--el-bg-color-overlay', c.bgElevated)
      root.style.setProperty('--el-text-color-primary', c.textPrimary)
      root.style.setProperty('--el-text-color-regular', c.textSecondary)
      root.style.setProperty('--el-text-color-secondary', c.textMuted)
      root.style.setProperty('--el-border-color', c.borderDefault)
      root.style.setProperty('--el-border-color-light', c.borderLight)
      root.style.setProperty('--el-fill-color-blank', c.bgInput)
      root.style.setProperty('--el-color-primary', c.colorPrimary)
      root.classList.add('dark-theme')
    } else {
      root.classList.remove('dark-theme')
      // Reset element-plus vars for light mode
      root.style.removeProperty('--el-bg-color')
      root.style.removeProperty('--el-bg-color-overlay')
      root.style.removeProperty('--el-text-color-primary')
      root.style.removeProperty('--el-text-color-regular')
      root.style.removeProperty('--el-text-color-secondary')
      root.style.removeProperty('--el-border-color')
      root.style.removeProperty('--el-border-color-light')
      root.style.removeProperty('--el-fill-color-blank')
      root.style.removeProperty('--el-color-primary')
    }
  }

  function setTheme(themeId: string) {
    const theme = THEMES.find(t => t.id === themeId)
    if (!theme) return
    currentThemeId.value = themeId
    currentTheme.value = theme
    localStorage.setItem('nesom-theme', themeId)
    applyTheme(theme)
  }

  // Apply on init
  function init() {
    applyTheme(currentTheme.value)
  }

  return { currentThemeId, currentTheme, setTheme, init, themes: THEMES }
})
