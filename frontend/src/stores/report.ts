/** Pinia store for report and statistics */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { DashboardResponse, ReportTemplate } from '@/types/report'
import { getDashboard, getReportTemplates } from '@/api/report'

export const useReportStore = defineStore('report', () => {
  const dashboard = ref<DashboardResponse | null>(null)
  const templates = ref<ReportTemplate[]>([])
  const loading = ref(false)
  const period = ref('month')

  async function loadDashboard(stationId?: string) {
    loading.value = true
    try {
      const res: any = await getDashboard({ station_id: stationId, period: period.value })
      dashboard.value = res
    } finally {
      loading.value = false
    }
  }

  async function loadTemplates(params?: { page?: number; category?: string; search?: string }) {
    loading.value = true
    try {
      const res: any = await getReportTemplates(params)
      templates.value = res.items ?? []
    } finally {
      loading.value = false
    }
  }

  return { dashboard, templates, loading, period, loadDashboard, loadTemplates }
})
