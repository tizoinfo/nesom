/** Work order management API */
import request from '@/utils/request'

// ── Work Orders ──────────────────────────────────────────────────────────────

export function getWorkOrders(params?: {
  page?: number
  page_size?: number
  station_id?: string
  status?: string
  work_order_type?: string
  priority?: string
  assigned_to?: string
  search?: string
}) {
  return request.get('/v1/work-orders', { params })
}

export function getWorkOrder(id: string) {
  return request.get(`/v1/work-orders/${id}`)
}

export function createWorkOrder(data: Record<string, unknown>) {
  return request.post('/v1/work-orders', data)
}

export function updateWorkOrder(id: string, data: Record<string, unknown>) {
  return request.patch(`/v1/work-orders/${id}`, data)
}

export function deleteWorkOrder(id: string) {
  return request.delete(`/v1/work-orders/${id}`)
}

// ── Status Transitions ───────────────────────────────────────────────────────

export function submitWorkOrder(id: string, data?: { submit_notes?: string }) {
  return request.post(`/v1/work-orders/${id}/submit`, data ?? {})
}

export function assignWorkOrder(id: string, data: { assigned_to: string; assigned_to_name: string; assign_notes?: string; scheduled_start?: string; scheduled_end?: string }) {
  return request.post(`/v1/work-orders/${id}/assign`, data)
}

export function startWorkOrder(id: string, data?: Record<string, unknown>) {
  return request.post(`/v1/work-orders/${id}/start`, data ?? {})
}

export function submitReview(id: string, data: { completion_notes?: string; completion_rate?: number; actual_duration?: number }) {
  return request.post(`/v1/work-orders/${id}/submit-review`, data)
}

export function approveWorkOrder(id: string, data?: { approve_notes?: string; actual_cost?: number }) {
  return request.post(`/v1/work-orders/${id}/approve`, data ?? {})
}

export function closeWorkOrder(id: string, data?: { close_notes?: string }) {
  return request.post(`/v1/work-orders/${id}/close`, data ?? {})
}

export function cancelWorkOrder(id: string, data: { cancel_reason: string; cancel_notes?: string }) {
  return request.post(`/v1/work-orders/${id}/cancel`, data)
}

// ── Templates ────────────────────────────────────────────────────────────────

export function getTemplates(params?: { work_order_type?: string; is_active?: boolean }) {
  return request.get('/v1/work-order-templates', { params })
}

export function createFromTemplate(templateId: string, data: Record<string, unknown>) {
  return request.post(`/v1/work-orders/from-template/${templateId}`, data)
}

// ── Statistics ───────────────────────────────────────────────────────────────

export function getCountStatistics(params?: { station_id?: string; start_date?: string; end_date?: string }) {
  return request.get('/v1/work-orders/statistics/count', { params })
}

export function getTimelinessStatistics(params?: { station_id?: string; start_date?: string; end_date?: string }) {
  return request.get('/v1/work-orders/statistics/timeliness', { params })
}

export function getPerformanceStatistics(params?: { user_id?: string; start_date?: string; end_date?: string }) {
  return request.get('/v1/work-orders/statistics/performance', { params })
}
