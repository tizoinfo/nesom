/** Work order management module types */

export type WorkOrderStatus = 'draft' | 'pending' | 'assigned' | 'in_progress' | 'pending_review' | 'completed' | 'closed' | 'cancelled'
export type WorkOrderType = 'repair' | 'inspection' | 'maintenance' | 'fault' | 'other'
export type Priority = 'low' | 'medium' | 'high' | 'emergency'

export interface WorkOrder {
  id: string
  work_order_no: string
  work_order_type: WorkOrderType
  title: string
  description?: string
  status: WorkOrderStatus
  priority: Priority
  emergency_level: string
  station_id: string
  device_id?: string
  device_name?: string
  device_code?: string
  reported_by?: string
  reported_by_name: string
  reported_at: string
  assigned_to?: string
  assigned_to_name?: string
  assigned_at?: string
  scheduled_start?: string
  scheduled_end?: string
  actual_start?: string
  actual_end?: string
  estimated_duration?: number
  actual_duration?: number
  completion_rate: number
  cost_estimate?: number
  actual_cost?: number
  location?: string
  images?: string[]
  tags?: Record<string, unknown>
  created_at: string
  updated_at: string
  closed_at?: string
  details?: WorkOrderDetailStep[]
  status_history?: StatusHistory[]
}

export interface WorkOrderDetailStep {
  id: number
  step_number: number
  step_title: string
  step_description?: string
  performed_by_name?: string
  started_at?: string
  completed_at?: string
  findings?: string
  actions_taken?: string
  quality_check: string
  created_at: string
}

export interface StatusHistory {
  id: number
  old_status: string
  new_status: string
  changed_by_name: string
  change_reason?: string
  change_notes?: string
  changed_at: string
}

export interface WorkOrderTemplate {
  id: string
  template_code: string
  template_name: string
  work_order_type: WorkOrderType
  priority: Priority
  estimated_duration: number
  cost_estimate?: number
  description_template: string
  steps_template: { step_title: string; step_description?: string }[]
  is_active: boolean
  used_count: number
}

export interface CountStatistics {
  total: number
  by_status: Record<string, number>
  by_type: Record<string, number>
  by_priority: Record<string, number>
}

export const STATUS_MAP: Record<WorkOrderStatus, { label: string; color: string; type: string }> = {
  draft: { label: '草稿', color: '#bfbfbf', type: 'info' },
  pending: { label: '待分配', color: '#fa8c16', type: 'warning' },
  assigned: { label: '已分配', color: '#1890ff', type: '' },
  in_progress: { label: '进行中', color: '#722ed1', type: '' },
  pending_review: { label: '待审核', color: '#eb2f96', type: '' },
  completed: { label: '已完成', color: '#52c41a', type: 'success' },
  closed: { label: '已关闭', color: '#8c8c8c', type: 'info' },
  cancelled: { label: '已取消', color: '#f5222d', type: 'danger' },
}

export const PRIORITY_MAP: Record<Priority, { label: string; color: string; type: string }> = {
  low: { label: '低', color: '#52c41a', type: 'success' },
  medium: { label: '中', color: '#1890ff', type: '' },
  high: { label: '高', color: '#fa8c16', type: 'warning' },
  emergency: { label: '紧急', color: '#f5222d', type: 'danger' },
}

export const TYPE_MAP: Record<WorkOrderType, string> = {
  repair: '维修',
  inspection: '巡检',
  maintenance: '保养',
  fault: '故障',
  other: '其他',
}
