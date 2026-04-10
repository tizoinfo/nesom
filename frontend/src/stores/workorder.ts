/** Pinia store for work order management */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { WorkOrder, CountStatistics } from '@/types/workorder'
import { getWorkOrders, getCountStatistics } from '@/api/workorder'

export const useWorkOrderStore = defineStore('workorder', () => {
  const workOrders = ref<WorkOrder[]>([])
  const loading = ref(false)
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const countStats = ref<CountStatistics | null>(null)

  async function loadWorkOrders(params?: {
    page?: number
    page_size?: number
    station_id?: string
    status?: string
    work_order_type?: string
    priority?: string
    search?: string
  }) {
    loading.value = true
    try {
      const res: any = await getWorkOrders(params)
      workOrders.value = res.items ?? []
      total.value = res.total ?? 0
      page.value = res.page ?? 1
      pageSize.value = res.page_size ?? 20
    } finally {
      loading.value = false
    }
  }

  async function loadCountStats(params?: { station_id?: string; start_date?: string; end_date?: string }) {
    try {
      countStats.value = await getCountStatistics(params) as any
    } catch {
      countStats.value = null
    }
  }

  return { workOrders, loading, total, page, pageSize, countStats, loadWorkOrders, loadCountStats }
})
