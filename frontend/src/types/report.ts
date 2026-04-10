/** Report and statistics module types */

export interface DashboardKPI {
  device_online_rate: number
  workorder_completion_rate: number
  inspection_completion_rate: number
  active_alerts: number
}

export interface DeviceStatsSummary {
  total_devices: number
  online_devices: number
  offline_devices: number
  fault_devices: number
  maintenance_devices: number
  avg_availability: number
  avg_oee: number
}

export interface StationDeviceStats {
  station_id: string
  device_count: number
  online_count: number
  offline_count: number
  fault_count: number
  availability: number
}

export interface DeviceTypeStats {
  device_type_id: string
  device_type_name: string
  device_count: number
  availability: number
}

export interface DeviceStatsResponse {
  summary: DeviceStatsSummary
  by_station: StationDeviceStats[]
  by_device_type: DeviceTypeStats[]
}

export interface WorkOrderStatsSummary {
  total_workorders: number
  completed_workorders: number
  pending_workorders: number
  in_progress_workorders: number
  overdue_workorders: number
  avg_completion_hours: number | null
  completion_rate: number
}

export interface WorkOrderTypeStats {
  work_order_type: string
  count: number
  completed: number
  avg_duration_hours: number | null
}

export interface WorkOrderPriorityStats {
  priority: string
  count: number
  completed: number
}

export interface WorkOrderStatsResponse {
  summary: WorkOrderStatsSummary
  by_type: WorkOrderTypeStats[]
  by_priority: WorkOrderPriorityStats[]
}

export interface InspectionStatsSummary {
  total_tasks: number
  completed_tasks: number
  pending_tasks: number
  overdue_tasks: number
  completion_rate: number
  problem_count: number
}

export interface DashboardResponse {
  kpi: DashboardKPI
  device_stats: DeviceStatsResponse
  workorder_stats: WorkOrderStatsResponse
  inspection_stats: InspectionStatsSummary
  generated_at: string
}

export interface ReportTemplate {
  id: string
  template_code: string
  template_name: string
  category: string
  sub_category?: string
  description?: string
  data_source_type: string
  parameter_definitions: Record<string, unknown>[]
  access_level: string
  created_by: string
  version: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ReportQueryColumn {
  field: string
  display_name: string
  data_type: string
}

export interface ReportQueryResult {
  columns: ReportQueryColumn[]
  rows: Record<string, unknown>[]
  summary?: Record<string, unknown>
}

export interface ReportExportTask {
  task_id: string
  status: string
  message: string
  progress?: number
  error_message?: string
  output_files?: Record<string, unknown>
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export const WORK_ORDER_TYPE_MAP: Record<string, string> = {
  repair: '维修',
  inspection: '巡检',
  maintenance: '保养',
  fault: '故障',
  other: '其他',
}

export const PRIORITY_MAP: Record<string, { label: string; color: string }> = {
  low: { label: '低', color: '#52c41a' },
  medium: { label: '中', color: '#1890ff' },
  high: { label: '高', color: '#fa8c16' },
  emergency: { label: '紧急', color: '#f5222d' },
}
