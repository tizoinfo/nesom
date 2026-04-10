/** System configuration API */
import request from '@/utils/request'
import type { SysConfig, SysDict, HealthStatus, PaginatedResponse } from '@/types/system'

// ── System Config ────────────────────────────────────────────────────────────

export function getConfigs(params?: {
  page?: number
  size?: number
  module?: string
  configKey?: string
  isSystem?: number
}) {
  return request.get<PaginatedResponse<SysConfig>>('/v1/configs', { params })
}

export function getConfig(configKey: string) {
  return request.get<SysConfig>(`/v1/configs/${configKey}`)
}

export function createConfig(data: Record<string, unknown>) {
  return request.post('/v1/configs', data)
}

export function updateConfig(configKey: string, data: Record<string, unknown>) {
  return request.put(`/v1/configs/${configKey}`, data)
}

export function deleteConfig(configKey: string) {
  return request.delete(`/v1/configs/${configKey}`)
}

export function refreshConfigCache() {
  return request.post('/v1/configs/cache/refresh')
}

// ── Dictionary ───────────────────────────────────────────────────────────────

export function getDictTypes() {
  return request.get<{ types: string[] }>('/v1/dict/types')
}

export function getDictData(dictType: string, status?: number) {
  return request.get<SysDict[]>('/v1/dict/data', { params: { dictType, status } })
}

export function createDictData(data: Record<string, unknown>) {
  return request.post('/v1/dict/data', data)
}

export function updateDictData(id: number, data: Record<string, unknown>) {
  return request.put(`/v1/dict/data/${id}`, data)
}

export function deleteDictData(id: number) {
  return request.delete(`/v1/dict/data/${id}`)
}

// ── Health ────────────────────────────────────────────────────────────────────

export function getSystemHealth() {
  return request.get<HealthStatus>('/v1/system/health')
}
