/** Inspection management API */
import request from '@/utils/request'

// ── Plans ────────────────────────────────────────────────────────────────────

export function getInspectionPlans(params?: {
  page?: number
  page_size?: number
  status?: string
  inspection_type?: string
  search?: string
}) {
  return request.get('/v1/inspection/plans', { params })
}

export function getInspectionPlan(id: string) {
  return request.get(`/v1/inspection/plans/${id}`)
}

export function createInspectionPlan(data: Record<string, unknown>) {
  return request.post('/v1/inspection/plans', data)
}

export function updateInspectionPlan(id: string, data: Record<string, unknown>) {
  return request.put(`/v1/inspection/plans/${id}`, data)
}

export function deleteInspectionPlan(id: string) {
  return request.delete(`/v1/inspection/plans/${id}`)
}

export function activatePlan(id: string) {
  return request.post(`/v1/inspection/plans/${id}/activate`)
}

export function pausePlan(id: string) {
  return request.post(`/v1/inspection/plans/${id}/pause`)
}

export function resumePlan(id: string) {
  return request.post(`/v1/inspection/plans/${id}/resume`)
}

export function cancelPlan(id: string) {
  return request.post(`/v1/inspection/plans/${id}/cancel`)
}

export function generateTasks(id: string, data: { start_date: string; end_date: string; override_existing?: boolean }) {
  return request.post(`/v1/inspection/plans/${id}/generate-tasks`, data)
}

// ── Tasks ────────────────────────────────────────────────────────────────────

export function getInspectionTasks(params?: {
  page?: number
  page_size?: number
  status?: string
  plan_id?: string
  assigned_to?: string
  priority?: string
  scheduled_date_gte?: string
  scheduled_date_lte?: string
  search?: string
}) {
  return request.get('/v1/inspection/tasks', { params })
}

export function getInspectionTask(id: string) {
  return request.get(`/v1/inspection/tasks/${id}`)
}

export function assignTask(id: string, data: { assigned_to: string; assigned_to_name: string }) {
  return request.post(`/v1/inspection/tasks/${id}/assign`, data)
}

export function startTask(id: string, data?: Record<string, unknown>) {
  return request.post(`/v1/inspection/tasks/${id}/start`, data ?? {})
}

export function completeTask(id: string, data?: Record<string, unknown>) {
  return request.post(`/v1/inspection/tasks/${id}/complete`, data ?? {})
}

export function reassignTask(id: string, data: { assigned_to: string; assigned_to_name: string; reason?: string }) {
  return request.put(`/v1/inspection/tasks/${id}/reassign`, data)
}

export function cancelTask(id: string) {
  return request.post(`/v1/inspection/tasks/${id}/cancel`)
}

// ── Statistics ───────────────────────────────────────────────────────────────

export function getInspectionStats(params?: { start_date?: string; end_date?: string }) {
  return request.get('/v1/inspection/stats', { params })
}
