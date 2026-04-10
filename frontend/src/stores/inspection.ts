/** Pinia store for inspection management */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { InspectionPlan, InspectionTask } from '@/types/inspection'
import { getInspectionPlans, getInspectionTasks, getInspectionStats } from '@/api/inspection'

export const useInspectionStore = defineStore('inspection', () => {
  const plans = ref<InspectionPlan[]>([])
  const tasks = ref<InspectionTask[]>([])
  const loading = ref(false)
  const totalPlans = ref(0)
  const totalTasks = ref(0)
  const stats = ref<Record<string, any> | null>(null)

  async function loadPlans(params?: Record<string, any>) {
    loading.value = true
    try {
      const res: any = await getInspectionPlans(params)
      plans.value = res.items ?? []
      totalPlans.value = res.total ?? 0
    } finally {
      loading.value = false
    }
  }

  async function loadTasks(params?: Record<string, any>) {
    loading.value = true
    try {
      const res: any = await getInspectionTasks(params)
      tasks.value = res.items ?? []
      totalTasks.value = res.total ?? 0
    } finally {
      loading.value = false
    }
  }

  async function loadStats(params?: Record<string, any>) {
    try {
      stats.value = await getInspectionStats(params) as any
    } catch {
      stats.value = null
    }
  }

  return { plans, tasks, loading, totalPlans, totalTasks, stats, loadPlans, loadTasks, loadStats }
})
