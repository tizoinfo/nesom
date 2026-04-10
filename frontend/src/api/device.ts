/** Device monitoring API */
import request from '@/utils/request'
import type { Device, DeviceAlert, DeviceMetric, DeviceType, PaginatedResponse } from '@/types/device'

// ── Device Types ─────────────────────────────────────────────────────────────

export function getDeviceTypes() {
  return request.get<DeviceType[]>('/v1/device-types')
}

// ── Devices ──────────────────────────────────────────────────────────────────

export function getDevices(params?: {
  page?: number
  page_size?: number
  station_id?: string
  status?: string
  device_type_id?: string
  search?: string
}) {
  return request.get<PaginatedResponse<Device>>('/v1/devices', { params })
}

export function getDevice(id: string) {
  return request.get<Device>(`/v1/devices/${id}`)
}

export function createDevice(data: Partial<Device>) {
  return request.post('/v1/devices', data)
}

export function updateDevice(id: string, data: Partial<Device>) {
  return request.put(`/v1/devices/${id}`, data)
}

export function deleteDevice(id: string) {
  return request.delete(`/v1/devices/${id}`)
}

// ── Heartbeat ────────────────────────────────────────────────────────────────

export function sendHeartbeat(deviceId: string) {
  return request.post(`/v1/devices/${deviceId}/heartbeat`)
}

// ── Metrics ──────────────────────────────────────────────────────────────────

export function getRealtimeMetrics(deviceId: string, metricTypes?: string) {
  return request.get(`/v1/devices/${deviceId}/metrics/realtime`, {
    params: metricTypes ? { metric_types: metricTypes } : undefined,
  })
}

export function getHistoricalMetrics(
  deviceId: string,
  params: {
    metric_type: string
    start_time: string
    end_time: string
    aggregation?: string
    limit?: number
  },
) {
  return request.get(`/v1/devices/${deviceId}/metrics/historical`, { params })
}

// ── Alerts ───────────────────────────────────────────────────────────────────

export function getDeviceAlerts(
  deviceId: string,
  params?: {
    status?: string
    alert_level?: string
    page?: number
    page_size?: number
  },
) {
  return request.get<PaginatedResponse<DeviceAlert>>(`/v1/devices/${deviceId}/alerts`, { params })
}

export function acknowledgeAlert(deviceId: string, alertId: number, notes?: string) {
  return request.post(`/v1/devices/${deviceId}/alerts/${alertId}/acknowledge`, { notes })
}

export function resolveAlert(deviceId: string, alertId: number, resolutionNotes: string) {
  return request.post(`/v1/devices/${deviceId}/alerts/${alertId}/resolve`, {
    resolution_notes: resolutionNotes,
  })
}
