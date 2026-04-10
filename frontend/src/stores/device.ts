/** Pinia store for device monitoring */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Device, DeviceStatus } from '@/types/device'
import { getDevices } from '@/api/device'

export const useDeviceStore = defineStore('device', () => {
  const devices = ref<Device[]>([])
  const loading = ref(false)
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)

  const statusStats = computed(() => {
    const stats: Record<DeviceStatus, number> = {
      online: 0,
      offline: 0,
      fault: 0,
      maintenance: 0,
      testing: 0,
      standby: 0,
    }
    devices.value.forEach((d) => {
      if (d.status in stats) stats[d.status]++
    })
    return stats
  })

  async function loadDevices(params?: {
    page?: number
    page_size?: number
    station_id?: string
    status?: string
    device_type_id?: string
    search?: string
  }) {
    loading.value = true
    try {
      const res: any = await getDevices(params)
      devices.value = res.items ?? []
      total.value = res.total ?? 0
      page.value = res.page ?? 1
      pageSize.value = res.page_size ?? 20
    } finally {
      loading.value = false
    }
  }

  return { devices, loading, total, page, pageSize, statusStats, loadDevices }
})
