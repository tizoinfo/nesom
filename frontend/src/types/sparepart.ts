/** Spare part management module types */

export type SparePartStatus = 'active' | 'inactive' | 'obsolete'
export type AlertSeverity = 'info' | 'warning' | 'error' | 'critical'

export interface SparePart {
  id: string
  spare_part_code: string
  spare_part_name: string
  category_id: string
  specification: string
  model?: string
  brand?: string
  unit: string
  status: SparePartStatus
  is_consumable: boolean
  is_controlled: boolean
  current_stock: number
  available_stock: number
  reserved_stock: number
  min_stock_level?: number
  max_stock_level?: number
  safety_stock_level?: number
  last_purchase_price?: number
  abc_classification?: string
  created_at: string
  updated_at: string
}

export interface SparePartCategory {
  id: string
  category_code: string
  category_name: string
  parent_id?: string
  level: number
  is_leaf: boolean
  unit: string
  description?: string
}

export interface InventoryAlert {
  alert_type: 'low_stock' | 'near_expiry'
  severity: AlertSeverity
  spare_part_id: string
  spare_part_code: string
  spare_part_name: string
  current_stock?: number
  threshold?: number
  difference?: number
  batch_no?: string
  expiry_date?: string
  days_remaining?: number
  quantity?: number
  total_value?: number
  alert_message: string
  suggested_action: string
  alert_time: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export const STATUS_MAP: Record<SparePartStatus, { label: string; color: string; type: string }> = {
  active: { label: '启用', color: '#52c41a', type: 'success' },
  inactive: { label: '停用', color: '#fa8c16', type: 'warning' },
  obsolete: { label: '淘汰', color: '#bfbfbf', type: 'info' },
}

export const SEVERITY_MAP: Record<AlertSeverity, { label: string; type: string }> = {
  info: { label: '信息', type: 'info' },
  warning: { label: '警告', type: 'warning' },
  error: { label: '错误', type: 'danger' },
  critical: { label: '严重', type: 'danger' },
}
