/** Pinia store for spare part management */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SparePart, SparePartCategory, InventoryAlert } from '@/types/sparepart'
import { getSpareParts, getCategories, getInventoryAlerts } from '@/api/sparepart'

export const useSparePartStore = defineStore('sparepart', () => {
  const spareParts = ref<SparePart[]>([])
  const categories = ref<SparePartCategory[]>([])
  const alerts = ref<InventoryAlert[]>([])
  const loading = ref(false)
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)

  async function loadSpareParts(params?: {
    page?: number
    page_size?: number
    category_id?: string
    status?: string
    brand?: string
    keyword?: string
    low_stock_only?: boolean
  }) {
    loading.value = true
    try {
      const res: any = await getSpareParts(params)
      spareParts.value = res.items ?? []
      total.value = res.total ?? 0
      page.value = res.page ?? 1
      pageSize.value = res.page_size ?? 20
    } finally {
      loading.value = false
    }
  }

  async function loadCategories() {
    try {
      const res: any = await getCategories()
      categories.value = Array.isArray(res) ? res : []
    } catch {
      categories.value = []
    }
  }

  async function loadAlerts(params?: { alert_type?: string; severity?: string }) {
    try {
      const res: any = await getInventoryAlerts(params)
      alerts.value = Array.isArray(res) ? res : []
    } catch {
      alerts.value = []
    }
  }

  return { spareParts, categories, alerts, loading, total, page, pageSize, loadSpareParts, loadCategories, loadAlerts }
})
