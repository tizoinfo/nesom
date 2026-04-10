/** Report and statistics API */
import request from '@/utils/request'
import type {
  DashboardResponse,
  DeviceStatsResponse,
  WorkOrderStatsResponse,
  InspectionStatsSummary,
  ReportTemplate,
  ReportQueryResult,
  ReportExportTask,
  PaginatedResponse,
} from '@/types/report'

// ── Dashboard / Stats ────────────────────────────────────────────────────────

export function getDashboard(params?: { station_id?: string; period?: string }) {
  return request.get<DashboardResponse>('/v1/stats/dashboard', { params })
}

export function getDeviceStats(params?: { station_id?: string }) {
  return request.get<DeviceStatsResponse>('/v1/stats/device', { params })
}

export function getWorkOrderStats(params?: { station_id?: string; period?: string }) {
  return request.get<WorkOrderStatsResponse>('/v1/stats/workorder', { params })
}

export function getInspectionStats(params?: { station_id?: string; period?: string }) {
  return request.get<InspectionStatsSummary>('/v1/stats/inspection', { params })
}

// ── Report Templates ─────────────────────────────────────────────────────────

export function getReportTemplates(params?: {
  page?: number
  page_size?: number
  category?: string
  search?: string
  is_active?: boolean
}) {
  return request.get<PaginatedResponse<ReportTemplate>>('/v1/reports/templates', { params })
}

export function getReportTemplate(id: string) {
  return request.get<ReportTemplate>(`/v1/reports/templates/${id}`)
}

export function createReportTemplate(data: Partial<ReportTemplate>) {
  return request.post('/v1/reports/templates', data)
}

export function updateReportTemplate(id: string, data: Partial<ReportTemplate>) {
  return request.put(`/v1/reports/templates/${id}`, data)
}

export function deleteReportTemplate(id: string) {
  return request.delete(`/v1/reports/templates/${id}`)
}

// ── Report Query ─────────────────────────────────────────────────────────────

export function executeReportQuery(data: {
  template_id: string
  parameters?: Record<string, unknown>
  page?: number
  page_size?: number
  enable_cache?: boolean
}) {
  return request.post<ReportQueryResult>('/v1/reports/query', data)
}

// ── Report Export ────────────────────────────────────────────────────────────

export function exportReport(
  templateId: string,
  data: { parameters?: Record<string, unknown>; format?: string; options?: Record<string, unknown> },
) {
  return request.post<ReportExportTask>(`/v1/reports/${templateId}/export`, data)
}

export function getExportTaskStatus(taskId: string) {
  return request.get<ReportExportTask>(`/v1/reports/tasks/${taskId}`)
}
