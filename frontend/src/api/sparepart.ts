/** Spare part management API */
import request from '@/utils/request'
import type { SparePart, SparePartCategory, InventoryAlert, PaginatedResponse } from '@/types/sparepart'

// ── Categories ───────────────────────────────────────────────────────────────

export function getCategories() {
  return request.get<SparePartCategory[]>('/v1/spare-part-categories')
}

// ── Spare Parts ──────────────────────────────────────────────────────────────

export function getSpareParts(params?: {
  page?: number
  page_size?: number
  category_id?: string
  status?: string
  brand?: string
  keyword?: string
  low_stock_only?: boolean
  abc_classification?: string
}) {
  return request.get<PaginatedResponse<SparePart>>('/v1/spare-parts', { params })
}

export function getSparePart(id: string) {
  return request.get<SparePart>(`/v1/spare-parts/${id}`)
}

export function createSparePart(data: Record<string, unknown>) {
  return request.post('/v1/spare-parts', data)
}

export function updateSparePart(id: string, data: Record<string, unknown>) {
  return request.patch(`/v1/spare-parts/${id}`, data)
}

export function deleteSparePart(id: string) {
  return request.delete(`/v1/spare-parts/${id}`)
}

// ── Inventory ────────────────────────────────────────────────────────────────

export function receiveStock(data: Record<string, unknown>) {
  return request.post('/v1/inventory/receive', data)
}

export function issueStock(data: Record<string, unknown>) {
  return request.post('/v1/inventory/issue', data)
}

// ── Alerts ───────────────────────────────────────────────────────────────────

export function getInventoryAlerts(params?: { alert_type?: string; severity?: string }) {
  return request.get<InventoryAlert[]>('/v1/alerts/inventory', { params })
}
