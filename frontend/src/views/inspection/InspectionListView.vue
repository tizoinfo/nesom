<template>
  <div class="inspection-page">
    <!-- Stats Overview -->
    <div class="stats-grid">
      <div v-for="item in statsCards" :key="item.key" class="stat-card">
        <div class="stat-value font-mono" :style="{ color: item.color }">{{ item.value }}</div>
        <div class="stat-label">{{ item.label }}</div>
      </div>
    </div>

    <!-- Tabs -->
    <el-card>
      <el-tabs v-model="activeTab">
        <!-- Plans Tab -->
        <el-tab-pane label="巡检计划" name="plans">
          <div class="tab-toolbar">
            <el-input v-model="planSearch" placeholder="搜索计划名称" clearable style="width: 220px" @keyup.enter="fetchPlans" />
            <el-select v-model="planStatusFilter" placeholder="状态" clearable style="width: 120px" @change="fetchPlans">
              <el-option v-for="(info, key) in planStatusEntries" :key="key" :label="info.label" :value="key" />
            </el-select>
            <el-button type="primary" @click="fetchPlans">查询</el-button>
            <el-button type="success" @click="showCreatePlan = true">新建计划</el-button>
          </div>

          <el-table :data="store.plans" v-loading="store.loading" stripe>
            <el-table-column prop="plan_code" label="计划编码" width="200">
              <template #default="{ row }"><span class="font-mono">{{ row.plan_code }}</span></template>
            </el-table-column>
            <el-table-column prop="plan_name" label="计划名称" min-width="180" show-overflow-tooltip />
            <el-table-column label="类型" width="100">
              <template #default="{ row }">{{ typeMap[row.inspection_type] ?? row.inspection_type }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getPlanStatusType(row.status)" size="small">{{ getPlanStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="优先级" width="80">
              <template #default="{ row }">
                <el-tag :type="getPriorityType(row.priority)" size="small">{{ getPriorityLabel(row.priority) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="frequency_type" label="频率" width="80" />
            <el-table-column prop="start_date" label="开始日期" width="120" />
            <el-table-column prop="created_by_name" label="创建人" width="100" />
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="goDetail(row.id)">详情</el-button>
                <el-button v-if="row.status === 'draft'" link type="success" size="small" @click="handleActivate(row.id)">激活</el-button>
                <el-button v-if="row.status === 'active'" link type="warning" size="small" @click="handlePause(row.id)">暂停</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination class="pagination" v-model:current-page="planPage" :total="store.totalPlans" :page-size="20" layout="total, prev, pager, next" @current-change="fetchPlans" />
        </el-tab-pane>

        <!-- Tasks Tab -->
        <el-tab-pane label="巡检任务" name="tasks">
          <div class="tab-toolbar">
            <el-input v-model="taskSearch" placeholder="搜索任务编码" clearable style="width: 220px" @keyup.enter="fetchTasks" />
            <el-select v-model="taskStatusFilter" placeholder="状态" clearable style="width: 120px" @change="fetchTasks">
              <el-option v-for="(info, key) in taskStatusEntries" :key="key" :label="info.label" :value="key" />
            </el-select>
            <el-button type="primary" @click="fetchTasks">查询</el-button>
          </div>

          <el-table :data="store.tasks" v-loading="store.loading" stripe>
            <el-table-column prop="task_code" label="任务编码" width="200">
              <template #default="{ row }"><span class="font-mono">{{ row.task_code }}</span></template>
            </el-table-column>
            <el-table-column prop="scheduled_date" label="计划日期" width="120" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getTaskStatusType(row.status)" size="small">{{ getTaskStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="优先级" width="80">
              <template #default="{ row }">
                <el-tag :type="getPriorityType(row.priority)" size="small">{{ getPriorityLabel(row.priority) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="assigned_to_name" label="执行人" width="100" />
            <el-table-column label="完成率" width="120">
              <template #default="{ row }"><el-progress :percentage="row.completion_rate" :stroke-width="6" /></template>
            </el-table-column>
            <el-table-column prop="problem_count" label="问题数" width="80" />
            <el-table-column label="创建时间" width="170">
              <template #default="{ row }"><span class="font-mono" style="font-size:12px">{{ formatTime(row.created_at) }}</span></template>
            </el-table-column>
          </el-table>
          <el-pagination class="pagination" v-model:current-page="taskPage" :total="store.totalTasks" :page-size="20" layout="total, prev, pager, next" @current-change="fetchTasks" />
        </el-tab-pane>

        <!-- Stats Tab -->
        <el-tab-pane label="统计报告" name="stats">
          <div class="stats-detail-grid">
            <el-card>
              <template #header>按状态分布</template>
              <div v-if="store.stats?.by_status" class="stats-list">
                <div v-for="(count, status) in store.stats.by_status" :key="status" class="stats-item">
                  <el-tag :type="getTaskStatusType(status as string)" size="small">{{ getTaskStatusLabel(status as string) }}</el-tag>
                  <span class="stats-count font-mono">{{ count }}</span>
                </div>
              </div>
              <el-empty v-else description="暂无数据" />
            </el-card>
            <el-card>
              <template #header>概览</template>
              <div v-if="store.stats?.overview" class="stats-list">
                <div class="stats-item"><span>总任务数</span><span class="stats-count font-mono">{{ store.stats.overview.total_tasks }}</span></div>
                <div class="stats-item"><span>已完成</span><span class="stats-count font-mono text-success">{{ store.stats.overview.completed_tasks }}</span></div>
                <div class="stats-item"><span>完成率</span><span class="stats-count font-mono text-primary-color">{{ store.stats.overview.completion_rate }}%</span></div>
                <div class="stats-item"><span>发现问题</span><span class="stats-count font-mono text-danger">{{ store.stats.overview.problem_count }}</span></div>
              </div>
              <el-empty v-else description="暂无数据" />
            </el-card>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- Create Plan Dialog -->
    <el-dialog v-model="showCreatePlan" title="新建巡检计划" width="600px" destroy-on-close>
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="计划名称" required><el-input v-model="createForm.plan_name" placeholder="请输入计划名称" /></el-form-item>
        <el-form-item label="巡检类型">
          <el-select v-model="createForm.inspection_type">
            <el-option v-for="(label, key) in typeMap" :key="key" :label="label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="createForm.priority">
            <el-option v-for="(info, key) in priorityEntries" :key="key" :label="info.label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="频率类型">
          <el-select v-model="createForm.frequency_type">
            <el-option label="每日" value="daily" /><el-option label="每周" value="weekly" />
            <el-option label="每月" value="monthly" /><el-option label="每季度" value="quarterly" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始日期" required>
          <el-date-picker v-model="createForm.start_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
        </el-form-item>
        <el-form-item label="描述"><el-input v-model="createForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreatePlan = false">取消</el-button>
        <el-button type="primary" @click="handleCreatePlan" :loading="creating">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useInspectionStore } from '@/stores/inspection'
import { createInspectionPlan, activatePlan, pausePlan } from '@/api/inspection'
import { PLAN_STATUS_MAP, TASK_STATUS_MAP, PRIORITY_MAP, INSPECTION_TYPE_MAP } from '@/types/inspection'

const router = useRouter()
const store = useInspectionStore()

const activeTab = ref('plans')
const planSearch = ref('')
const planStatusFilter = ref('')
const planPage = ref(1)
const taskSearch = ref('')
const taskStatusFilter = ref('')
const taskPage = ref(1)
const showCreatePlan = ref(false)
const creating = ref(false)

const planStatusEntries = PLAN_STATUS_MAP
const taskStatusEntries = TASK_STATUS_MAP
const priorityEntries = PRIORITY_MAP
const typeMap = INSPECTION_TYPE_MAP

const createForm = ref({ plan_name: '', description: '', inspection_type: 'routine', priority: 'medium', frequency_type: 'weekly', start_date: '' })

const statsCards = computed(() => {
  const o = store.stats?.overview
  return [
    { key: 'total', label: '总任务数', value: o?.total_tasks ?? 0, color: '#3B82F6' },
    { key: 'completed', label: '已完成', value: o?.completed_tasks ?? 0, color: '#22C55E' },
    { key: 'rate', label: '完成率', value: `${o?.completion_rate ?? 0}%`, color: '#F59E0B' },
    { key: 'problems', label: '发现问题', value: o?.problem_count ?? 0, color: '#EF4444' },
  ]
})

function getPlanStatusLabel(s: string) { return (PLAN_STATUS_MAP as any)[s]?.label ?? s }
function getPlanStatusType(s: string) { return (PLAN_STATUS_MAP as any)[s]?.type ?? '' }
function getTaskStatusLabel(s: string) { return (TASK_STATUS_MAP as any)[s]?.label ?? s }
function getTaskStatusType(s: string) { return (TASK_STATUS_MAP as any)[s]?.type ?? '' }
function getPriorityLabel(p: string) { return (PRIORITY_MAP as any)[p]?.label ?? p }
function getPriorityType(p: string) { return (PRIORITY_MAP as any)[p]?.type ?? '' }
function formatTime(iso: string) { return new Date(iso).toLocaleString('zh-CN') }

function fetchPlans() {
  store.loadPlans({ page: planPage.value, page_size: 20, status: planStatusFilter.value || undefined, search: planSearch.value || undefined })
}
function fetchTasks() {
  store.loadTasks({ page: taskPage.value, page_size: 20, status: taskStatusFilter.value || undefined, search: taskSearch.value || undefined })
}

function goDetail(id: string) { router.push(`/inspection/plans/${id}`) }

async function handleActivate(id: string) {
  try { await activatePlan(id); ElMessage.success('计划已激活'); fetchPlans() } catch { ElMessage.error('激活失败') }
}
async function handlePause(id: string) {
  try { await pausePlan(id); ElMessage.success('计划已暂停'); fetchPlans() } catch { ElMessage.error('暂停失败') }
}

async function handleCreatePlan() {
  if (!createForm.value.plan_name || !createForm.value.start_date) { ElMessage.warning('请填写计划名称和开始日期'); return }
  creating.value = true
  try {
    await createInspectionPlan({ ...createForm.value, created_by: 'current_user', created_by_name: '当前用户' })
    ElMessage.success('巡检计划创建成功')
    showCreatePlan.value = false
    createForm.value = { plan_name: '', description: '', inspection_type: 'routine', priority: 'medium', frequency_type: 'weekly', start_date: '' }
    fetchPlans()
  } catch { ElMessage.error('创建失败') } finally { creating.value = false }
}

onMounted(() => { fetchPlans(); fetchTasks(); store.loadStats() })
</script>

<style scoped>
.inspection-page { display: flex; flex-direction: column; gap: var(--grid-gap); }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.stat-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--card-radius);
  padding: 16px;
  text-align: center;
}
.stat-value { font-size: 28px; font-weight: 700; }
.stat-label { font-size: 13px; color: var(--text-muted); margin-top: 4px; }

.tab-toolbar { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; }
.pagination { margin-top: 16px; justify-content: flex-end; }

.stats-detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--grid-gap); }
.stats-list { display: flex; flex-direction: column; gap: 0; }
.stats-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--border-light); }
.stats-item:last-child { border-bottom: none; }
.stats-count { font-weight: 600; font-size: 16px; }

@media (max-width: 768px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .stats-detail-grid { grid-template-columns: 1fr; }
}
</style>
