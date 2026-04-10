<template>
  <div class="plan-detail">
    <el-page-header @back="router.back()" :content="plan?.plan_name ?? '巡检计划详情'" />

    <el-card v-loading="loading">
      <template #header><span>基本信息</span></template>
      <el-descriptions :column="2" border v-if="plan">
        <el-descriptions-item label="计划编码"><span class="font-mono">{{ plan.plan_code }}</span></el-descriptions-item>
        <el-descriptions-item label="计划名称">{{ plan.plan_name }}</el-descriptions-item>
        <el-descriptions-item label="巡检类型">{{ typeMap[plan.inspection_type] ?? plan.inspection_type }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getPlanStatusType(plan.status)" size="small">{{ getPlanStatusLabel(plan.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="优先级">
          <el-tag :type="getPriorityType(plan.priority)" size="small">{{ getPriorityLabel(plan.priority) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="频率类型">{{ plan.frequency_type }}</el-descriptions-item>
        <el-descriptions-item label="开始日期">{{ plan.start_date }}</el-descriptions-item>
        <el-descriptions-item label="结束日期">{{ plan.end_date ?? '无' }}</el-descriptions-item>
        <el-descriptions-item label="创建人">{{ plan.created_by_name }}</el-descriptions-item>
        <el-descriptions-item label="创建时间"><span class="font-mono" style="font-size:13px">{{ formatTime(plan.created_at) }}</span></el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">{{ plan.description ?? '无' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>关联任务</span>
          <el-button v-if="plan?.status === 'active' || plan?.status === 'draft'" type="primary" size="small" @click="showGenerate = true">生成任务</el-button>
        </div>
      </template>
      <el-table :data="tasks" v-loading="tasksLoading" stripe>
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
          <template #default="{ row }"><el-progress :percentage="row.completion_rate ?? 0" :stroke-width="6" /></template>
        </el-table-column>
        <el-table-column prop="problem_count" label="问题数" width="80" />
      </el-table>
    </el-card>

    <el-dialog v-model="showGenerate" title="生成巡检任务" width="400px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="开始日期"><el-date-picker v-model="genStart" type="date" value-format="YYYY-MM-DD" /></el-form-item>
        <el-form-item label="结束日期"><el-date-picker v-model="genEnd" type="date" value-format="YYYY-MM-DD" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGenerate = false">取消</el-button>
        <el-button type="primary" @click="handleGenerate" :loading="generating">生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getInspectionPlan, getInspectionTasks, generateTasks } from '@/api/inspection'
import { PLAN_STATUS_MAP, TASK_STATUS_MAP, PRIORITY_MAP, INSPECTION_TYPE_MAP } from '@/types/inspection'

const route = useRoute()
const router = useRouter()

const plan = ref<any>(null)
const tasks = ref<any[]>([])
const loading = ref(false)
const tasksLoading = ref(false)
const showGenerate = ref(false)
const generating = ref(false)
const genStart = ref('')
const genEnd = ref('')
const typeMap = INSPECTION_TYPE_MAP

function getPlanStatusLabel(s: string) { return (PLAN_STATUS_MAP as any)[s]?.label ?? s }
function getPlanStatusType(s: string) { return (PLAN_STATUS_MAP as any)[s]?.type ?? '' }
function getTaskStatusLabel(s: string) { return (TASK_STATUS_MAP as any)[s]?.label ?? s }
function getTaskStatusType(s: string) { return (TASK_STATUS_MAP as any)[s]?.type ?? '' }
function getPriorityLabel(p: string) { return (PRIORITY_MAP as any)[p]?.label ?? p }
function getPriorityType(p: string) { return (PRIORITY_MAP as any)[p]?.type ?? '' }
function formatTime(iso: string) { return iso ? new Date(iso).toLocaleString('zh-CN') : '' }

async function loadPlan() {
  loading.value = true
  try { plan.value = await getInspectionPlan(route.params.id as string) }
  catch { ElMessage.error('加载计划详情失败') }
  finally { loading.value = false }
}

async function loadTasks() {
  tasksLoading.value = true
  try { const res: any = await getInspectionTasks({ plan_id: route.params.id as string, page_size: 50 }); tasks.value = res?.items ?? [] }
  catch { /* ignore */ }
  finally { tasksLoading.value = false }
}

async function handleGenerate() {
  if (!genStart.value || !genEnd.value) { ElMessage.warning('请选择日期范围'); return }
  generating.value = true
  try {
    const res: any = await generateTasks(route.params.id as string, { start_date: genStart.value, end_date: genEnd.value })
    ElMessage.success(`成功生成 ${res?.generated_count ?? 0} 个任务`)
    showGenerate.value = false; loadTasks()
  } catch { ElMessage.error('生成任务失败') } finally { generating.value = false }
}

onMounted(() => { loadPlan(); loadTasks() })
</script>

<style scoped>
.plan-detail { display: flex; flex-direction: column; gap: var(--grid-gap); }
</style>
