/** Pinia store for system configuration */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SysConfig, SysDict, HealthStatus } from '@/types/system'
import { getConfigs, getDictTypes, getDictData, getSystemHealth } from '@/api/system'

export const useSystemStore = defineStore('system', () => {
  const configs = ref<SysConfig[]>([])
  const dictTypes = ref<string[]>([])
  const dictData = ref<SysDict[]>([])
  const health = ref<HealthStatus | null>(null)
  const loading = ref(false)
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)

  async function loadConfigs(params?: {
    page?: number
    size?: number
    module?: string
    configKey?: string
  }) {
    loading.value = true
    try {
      const res: any = await getConfigs(params)
      configs.value = res.items ?? []
      total.value = res.total ?? 0
      page.value = res.page ?? 1
      pageSize.value = res.page_size ?? 20
    } finally {
      loading.value = false
    }
  }

  async function loadDictTypes() {
    try {
      const res: any = await getDictTypes()
      dictTypes.value = res.types ?? []
    } catch {
      dictTypes.value = []
    }
  }

  async function loadDictData(dictType: string) {
    loading.value = true
    try {
      const res: any = await getDictData(dictType)
      dictData.value = Array.isArray(res) ? res : []
    } finally {
      loading.value = false
    }
  }

  async function loadHealth() {
    try {
      const res: any = await getSystemHealth()
      health.value = res
    } catch {
      health.value = null
    }
  }

  return {
    configs, dictTypes, dictData, health, loading, total, page, pageSize,
    loadConfigs, loadDictTypes, loadDictData, loadHealth,
  }
})
