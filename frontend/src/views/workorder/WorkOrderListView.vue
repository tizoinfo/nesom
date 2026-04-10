<template>
  <div class="workorder-page">
    <!-- Status Summary Cards -->
    <div class="status-grid">
      <div
        v-for="(info, key) in statusEntries"
        :key="key"
        class="status-card"
        :class="{ active: statusFilter === key }"
        @click="filterByStatus(key as string)"
      >
        <div class="status-indicator" :style="{ background: info.color }"></div>
        <div class="status-count font-mono">{{ store.countStats?.by_status?.[key] ?? 0 }}</div>
        <div class="status-label">{{ info.label }}</div>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <el-input v-model="search" placeholder="搜索工单编号/标题" clearable style="width: 220px" @clear="handleSearch" @keyup.enter="handleSearch" />
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 120px" @change="handleSearch">
        <el-option v-for="(info, key) in statusEntries" :key="key" :label="info.label" :value="key" />
      </el-select>
      <el-select v-model="typeFilter" placeholder="类型" clearable style="width: 120px" @change="handleSearch">
        <el-option v-for="(label, key) in typeEntries" :key="key" :label="label" :value="key" />
      </el-select>
      <el-select v-model="priorityFilter" placeholder="优先级" clearable style="width: 120px" @change="handleSearch">
        <el-option v-for="(info, key) in priorityEntries" :key="key" :label="info.label" :value="key" />
      </el-select>
      <el-button type="primary" @click="handleSearch">查询</el-button>
      <el-button type="success" @click="showCreate = true">新建工单</el-button>
    </div>

    <!-- View Toggle + Table -->
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:flex-end">
          <el-radio-group v-model="viewMode" size="small">
            <el-radio-button value="table">表格</el-radio-button>
            <el-radio-button value="card">卡片</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <!-- Table View -->
      <el-table v-if="viewMode === 'table'" :data="store.workOrders" v-loading="store.loading" stripe>
        <el-table-column prop="work_order_no" label="工单编号" width="200">
          <template #default="{ row }"><span class="font-mono">{{ row.work_order_no }}</span></template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
        <el-table-column label="类型" width="80">
          <template #default="{ row }">{{ typeEntries[row.work_order_type] ?? row.work_order_type }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="80">
          <template #default="{ row }">
            <el-tag :type="getPriorityType(row.priority)" size="small">{{ getPriorityLabel(row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reported_by_name" label="上报人" width="100" />
        <el-table-column prop="assigned_to_name" label="执行人" width="100" />
        <el-table-column label="上报时间" width="170">
          <template #default="{ row }"><span class="font-mono" style="font-size:12px">{{ formatTime(row.reported_at) }}</span></template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="goDetail(row.id)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- Card View -->
      <div v-else class="card-grid">
        <div v-for="wo in store.workOrders" :key="wo.id" class="wo-card" @click="goDetail(wo.id)">
          <div class="wo-card-header">
            <el-tag :type="getStatusType(wo.status)" size="small">{{ getStatusLabel(wo.status) }}</el-tag>
            <el-tag :type="getPriorityType(wo.priority)" size="small">{{ getPriorityLabel(wo.priority) }}</el-tag>
          </div>
          <div class="wo-card-title">{{ wo.title }}</div>
          <div class="wo-card-no font-mono">{{ wo.work_order_no }}</div>
          <div class="wo-card-meta">
            <span>{{ wo.reported_by_name }}</span>
            <span class="font-mono">{{ formatTime(wo.reported_at) }}</span>
          </div>
        </div>
      </div>

      <el-pagination
        class="pagination"
        v-model:current-page="currentPage"
        v-model:page-size="currentPageSize"
        :total="store.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </el-card>

    <!-- Create Dialog -->
    <el-dialog v-model="showCreate" title="新建工单" width="600px" destroy-on-close>
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="标题" required>
          <el-input v-model="createForm.title" placeholder="请输入工单标题" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="createForm.work_order_type">
            <el-option v-for="(label, key) in typeEntries" :key="key" :label="label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="createForm.priority">
            <el-option v-for="(info, key) in priorityEntries" :key="key" :label="info.label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述" required>
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="请输入工单描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useWorkOrderStore } from '@/stores/workorder'
import { useUserStore } from '@/stores/user'
import { createWorkOrder, getWorkOrders } from '@/api/workorder'
import { STATUS_MAP, PRIORITY_MAP, TYPE_MAP } from '@/types/workorder'
import type { WorkOrderStatus, Priority } from '@/types/workorder'

const router = useRouter()
const store = useWorkOrderStore()
const userStore = useUserStore()

const search = ref('')
const statusFilter = ref('')
const typeFilter = ref('')
const priorityFilter = ref('')
const currentPage = ref(1)
const currentPageSize = ref(20)
const viewMode = ref<'table' | 'card'>('table')
const showCreate = ref(false)
const creating = ref(false)

const statusEntries = STATUS_MAP
const priorityEntries = PRIORITY_MAP
const typeEntries = TYPE_MAP

const createForm = ref({
  title: '', description: '', work_order_type: 'repair', priority: 'medium', station_id: '',
})

async function loadDefaultStation() {
  try {
    const stored = localStorage.getItem('nesom-station-id')
    if (stored) { createForm.value.station_id = stored; return }
    const res: any = await getWorkOrders({ page: 1, page_size: 1 })
    const sid = res?.items?.[0]?.station_id
    if (sid) { createForm.value.station_id = sid; localStorage.setItem('nesom-station-id', sid) }
  } catch { /* ignore */ }
}

function getStatusLabel(s: WorkOrderStatus) { return STATUS_MAP[s]?.label ?? s }
function getStatusType(s: WorkOrderStatus) { return STATUS_MAP[s]?.type ?? '' }
function getPriorityLabel(p: Priority) { return PRIORITY_MAP[p]?.label ?? p }
function getPriorityType(p: Priority) { return PRIORITY_MAP[p]?.type ?? '' }
function formatTime(iso: string) { return new Date(iso).toLocaleString('zh-CN') }

function filterByStatus(status: string) {
  statusFilter.value = statusFilter.value === status ? '' : status
  handleSearch()
}

function handleSearch() { currentPage.value = 1; fetchData() }
function handlePageChange(p: number) { currentPage.value = p; fetchData() }
function handleSizeChange(s: number) { currentPageSize.value = s; currentPage.value = 1; fetchData() }

function fetchData() {
  store.loadWorkOrders({
    page: currentPage.value, page_size: currentPageSize.value,
    status: statusFilter.value || undefined,
    work_order_type: typeFilter.value || undefined,
    priority: priorityFilter.value || undefined,
    search: search.value || undefined,
  })
  store.loadCountStats()
}

function goDetail(id: string) { router.push(`/workorders/${id}`) }

async function handleCreate() {
  if (!createForm.value.title || !createForm.value.description) {
    ElMessage.warning('请填写标题和描述'); return
  }
  creating.value = true
  try {
    await createWorkOrder({
      ...createForm.value,
      emergency_level: 'normal',
      station_id: createForm.value.station_id,
      reported_by: userStore.userInfo?.id ?? '',
      reported_by_name: (userStore.userInfo as any)?.real_name ?? (userStore.userInfo as any)?.realName ?? userStore.userInfo?.username ?? '',
    })
    ElMessage.success('工单创建成功')
    showCreate.value = false
    createForm.value = { title: '', description: '', work_order_type: 'repair', priority: 'medium', station_id: createForm.value.station_id }
    fetchData()
  } catch { ElMessage.error('创建失败') } finally { creating.value = false }
}

onMounted(() => { fetchData(); loadDefaultStation() })
</script>

<style scoped>
.workorder-page { display: flex; flex-direction: column; gap: var(--grid-gap); }

.status-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 10px;
}
.status-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--card-radius);
  padding: 12px;
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.status-card:hover { border-color: var(--bg-hover); }
.status-card.active { border-color: var(--color-primary); box-shadow: var(--shadow-glow-blue); }
.status-indicator { width: 8px; height: 8px; border-radius: 50%; }
.status-count { font-size: 20px; font-weight: 700; color: var(--text-primary); }
.status-label { font-size: 11px; color: var(--text-muted); }

.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.pagination { margin-top: 16px; justify-content: flex-end; }

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--grid-gap);
}
.wo-card {
  background: var(--bg-elevated);
  border: 1px solid var(--border-light);
  border-radius: 10px;
  padding: 16px;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.wo-card:hover { border-color: var(--color-primary); box-shadow: var(--shadow-md); }
.wo-card-header { display: flex; gap: 8px; margin-bottom: 10px; }
.wo-card-title { font-weight: 600; font-size: 14px; color: var(--text-primary); margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.wo-card-no { color: var(--text-muted); font-size: 12px; margin-bottom: 10px; }
.wo-card-meta { display: flex; justify-content: space-between; color: var(--text-muted); font-size: 12px; }

@media (max-width: 1200px) { .status-grid { grid-template-columns: repeat(4, 1fr); } }
@media (max-width: 640px) { .status-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
