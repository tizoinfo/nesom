<template>
  <div class="device-page">
    <div class="status-grid">
      <div v-for="(info, key) in statusEntries" :key="key" class="status-card" :class="{ active: statusFilter === key }" @click="filterByStatus(key)">
        <div class="status-indicator" :style="{ background: info.color }"></div>
        <div class="status-count font-mono">{{ deviceStore.statusStats[key] ?? 0 }}</div>
        <div class="status-label">{{ info.label }}</div>
      </div>
    </div>

    <div class="toolbar">
      <el-input v-model="search" placeholder="搜索设备编码/名称" clearable :prefix-icon="SearchIcon" style="width: 240px" @clear="handleSearch" @keyup.enter="handleSearch" />
      <el-select v-model="statusFilter" placeholder="设备状态" clearable style="width: 140px" @change="handleSearch">
        <el-option v-for="(info, key) in statusEntries" :key="key" :label="info.label" :value="key" />
      </el-select>
      <el-button type="primary" @click="handleSearch">查询</el-button>
    </div>

    <el-card>
      <el-table :data="deviceStore.devices" v-loading="deviceStore.loading" stripe>
        <el-table-column prop="device_code" label="设备编码" width="140"><template #default="{ row }"><span class="font-mono">{{ row.device_code }}</span></template></el-table-column>
        <el-table-column prop="device_name" label="设备名称" min-width="160" />
        <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="getStatusType(row.status)" size="small">{{ getStatusLabel(row.status) }}</el-tag></template></el-table-column>
        <el-table-column label="健康评分" width="100"><template #default="{ row }"><span class="font-mono" :style="{ color: getScoreColor(row.health_score), fontWeight: 600 }">{{ row.health_score ?? '--' }}</span></template></el-table-column>
        <el-table-column prop="manufacturer" label="制造商" width="120" />
        <el-table-column prop="model" label="型号" width="140" />
        <el-table-column label="最后心跳" width="170"><template #default="{ row }"><span class="font-mono" style="font-size:12px;color:var(--text-secondary)">{{ row.last_heartbeat ? formatTime(row.last_heartbeat) : '--' }}</span></template></el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="goDetail(row.id)">详情</el-button>
            <el-button link type="warning" size="small" @click="goAlerts(row.id)">告警</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="pagination" v-model:current-page="currentPage" v-model:page-size="currentPageSize" :total="deviceStore.total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @current-change="handlePageChange" @size-change="handleSizeChange" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, markRaw } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { useDeviceStore } from '@/stores/device'
import { STATUS_MAP } from '@/types/device'
import type { DeviceStatus } from '@/types/device'

const SearchIcon = markRaw(Search)
const router = useRouter()
const deviceStore = useDeviceStore()
const search = ref('')
const statusFilter = ref<string>('')
const currentPage = ref(1)
const currentPageSize = ref(20)
const statusEntries = STATUS_MAP

function getStatusLabel(status: DeviceStatus) { return STATUS_MAP[status]?.label ?? status }
function getStatusType(status: DeviceStatus) { return STATUS_MAP[status]?.type ?? '' }
function getScoreColor(score?: number) {
  if (!score) return 'var(--text-muted)'
  if (score >= 90) return '#10B981'
  if (score >= 70) return '#0891B2'
  if (score >= 50) return '#F59E0B'
  return '#EF4444'
}
function formatTime(iso: string) { return new Date(iso).toLocaleString('zh-CN') }
function filterByStatus(status: string) { statusFilter.value = statusFilter.value === status ? '' : status; handleSearch() }
function handleSearch() { currentPage.value = 1; fetchDevices() }
function handlePageChange(p: number) { currentPage.value = p; fetchDevices() }
function handleSizeChange(s: number) { currentPageSize.value = s; currentPage.value = 1; fetchDevices() }
function fetchDevices() { deviceStore.loadDevices({ page: currentPage.value, page_size: currentPageSize.value, status: statusFilter.value || undefined, search: search.value || undefined }) }
function goDetail(id: string) { router.push(`/devices/${id}`) }
function goAlerts(id: string) { router.push(`/devices/${id}/alerts`) }
onMounted(() => fetchDevices())
</script>

<style scoped>
.device-page { display: flex; flex-direction: column; gap: var(--grid-gap); }
.status-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; }
.status-card {
  background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: var(--card-radius);
  padding: 16px; cursor: pointer; transition: all var(--transition-fast);
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  box-shadow: var(--shadow-sm);
}
.status-card:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }
.status-card.active { border-color: var(--color-primary); box-shadow: var(--shadow-glow); }
.status-indicator { width: 8px; height: 8px; border-radius: 50%; }
.status-count { font-size: 24px; font-weight: 700; color: var(--text-primary); }
.status-label { font-size: 12px; color: var(--text-muted); }
.toolbar { display: flex; gap: 12px; align-items: center; }
.pagination { margin-top: 16px; justify-content: flex-end; }
@media (max-width: 1024px) { .status-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 640px) { .status-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
