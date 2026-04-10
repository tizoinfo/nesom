/** Inspection management module types */

export type InspectionType = 'routine' | 'special' | 'emergency'
export type PlanStatus = 'draft' | 'active' | 'paused' | 'completed' | 'cancelled'
export type TaskStatus = 'pending' | 'assigned' | 'in_progress' | 'completed' | 'cancelled' | 'overdue'
export type Priority = 'low' | 'medium' | 'high' | 'critical'

export interface InspectionPlan {
  id: string
  plan_code: string
  plan_name: string
  description?: string
  inspection_type: InspectionType
  priority: Priority
  status: PlanStatus
  frequency_type: string
  frequency_value?: number
  frequency_days?: number[]
  start_date: string
  end_date?: string
  start_time?: string
  end_time?: string
  estimated_duration?: number
  auto_assign: boolean
  assign_strategy: string
  require_photo: boolean
  require_gps: boolean
  require_signature: boolean
  created_by: string
  created_by_name: string
  created_at: string
  updated_at: string
}

export interface InspectionTask {
  id: string
  task_code: string
  plan_id: string
  scheduled_date: string
  scheduled_start_time?: string
  scheduled_end_time?: string
  assigned_to?: string
  assigned_to_name?: string
  status: TaskStatus
  priority: Priority
  total_checkpoints: number
  completed_checkpoints: number
  completion_rate: number
  problem_count: number
  is_offline: boolean
  created_at: string
}

export const PLAN_STATUS_MAP: Record<PlanStatus, { label: string; color: string; type: string }> = {
  draft: { label: '草稿', color: '#bfbfbf', type: 'info' },
  active: { label: '已激活', color: '#52c41a', type: 'success' },
  paused: { label: '已暂停', color: '#fa8c16', type: 'warning' },
  completed: { label: '已完成', color: '#1890ff', type: '' },
  cancelled: { label: '已取消', color: '#f5222d', type: 'danger' },
}

export const TASK_STATUS_MAP: Record<TaskStatus, { label: string; color: string; type: string }> = {
  pending: { label: '待分配', color: '#bfbfbf', type: 'info' },
  assigned: { label: '已分配', color: '#1890ff', type: '' },
  in_progress: { label: '进行中', color: '#722ed1', type: '' },
  completed: { label: '已完成', color: '#52c41a', type: 'success' },
  cancelled: { label: '已取消', color: '#f5222d', type: 'danger' },
  overdue: { label: '已过期', color: '#fa8c16', type: 'warning' },
}

export const PRIORITY_MAP: Record<Priority, { label: string; type: string }> = {
  low: { label: '低', type: 'success' },
  medium: { label: '中', type: '' },
  high: { label: '高', type: 'warning' },
  critical: { label: '紧急', type: 'danger' },
}

export const INSPECTION_TYPE_MAP: Record<InspectionType, string> = {
  routine: '例行巡检',
  special: '专项巡检',
  emergency: '应急巡检',
}
