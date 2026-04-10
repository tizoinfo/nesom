/** Device monitoring module types */

export type DeviceStatus = 'online' | 'offline' | 'fault' | 'maintenance' | 'testing' | 'standby'
export type AlertLevel = 'info' | 'warning' | 'error' | 'critical'
export type AlertStatus = 'active' | 'acknowledged' | 'resolved' | 'closed'

export interface DeviceType {
  id: string
  type_code: string
  type_name: string
  category?: string
  sub_category?: string
  description?: string
}

export interface Device {
  id: string
  device_code: string
  device_name: string
  device_type_id: string
  station_id: string
  status: DeviceStatus
  manufacturer?: string
  model?: string
  serial_number?: string
  rated_power?: number
  health_score?: number
  last_heartbeat?: string
  data_collection_status: string
  created_at: string
  updated_at: string
  // detail fields
  device_type?: DeviceType
  rated_voltage?: number
  rated_current?: number
  parameters?: Record<string, unknown>
  location_description?: string
  longitude?: number
  latitude?: number
  description?: string
  responsible_person_name?: string
}

export interface DeviceMetric {
  metric_type: string
  metric_value: number
  metric_unit: string
  collected_at: string
  quality: number
}

export interface DeviceAlert {
  id: number
  device_id: string
  alert_code: string
  alert_type: string
  alert_level: AlertLevel
  alert_title: string
  alert_message: string
  trigger_value?: number
  threshold_value?: number
  start_time: string
  end_time?: string
  status: AlertStatus
  acknowledged_at?: string
  acknowledged_by_name?: string
  resolved_at?: string
  resolved_by_name?: string
  resolution_notes?: string
  created_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export const STATUS_MAP: Record<DeviceStatus, { label: string; color: string; type: string }> = {
  online: { label: '在线', color: '#52c41a', type: 'success' },
  offline: { label: '离线', color: '#bfbfbf', type: 'info' },
  fault: { label: '故障', color: '#f5222d', type: 'danger' },
  maintenance: { label: '维护中', color: '#fa8c16', type: 'warning' },
  testing: { label: '测试中', color: '#1890ff', type: '' },
  standby: { label: '备用', color: '#722ed1', type: '' },
}

export const ALERT_LEVEL_MAP: Record<AlertLevel, { label: string; color: string; type: string }> = {
  info: { label: '信息', color: '#1890ff', type: 'info' },
  warning: { label: '警告', color: '#fa8c16', type: 'warning' },
  error: { label: '错误', color: '#f5222d', type: 'danger' },
  critical: { label: '严重', color: '#cf1322', type: 'danger' },
}
