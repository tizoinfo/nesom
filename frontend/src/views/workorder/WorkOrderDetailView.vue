<template>
  <div class="wo-detail-page" v-loading="loading">
    <el-page-header @back="router.back()" :title="'返回'" :content="workOrder?.title ?? '工单详情'" />

    <template v-if="workOrder">
      <el-card class="info-card">
        <template #header>
          <div class="card-header">
            <span>基本信息</span>
            <div class="header-tags">
              <el-tag :type="getStatusType(workOrder.status)" size="default">{{ getStatusLabel(workOrder.status) }}</el-tag>
              <el-tag :type="getPriorityType(workOrder.priority)" size="default">{{ getPriorityLabel(workOrder.priority) }}</el-tag>
            </div>
          </div>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="工单编号"><span class="font-mono">{{ workOrder.work_order_no }}</span></el-descriptions-item>
          <el-descriptions-item label="工单类型">{{ typeEntries[workOrder.work_order_type] }}</el-descriptions-item>
          <el-descriptions-item label="上报人">{{ workOrder.reported_by_name }}</el-descriptions-item>
          <el-descriptions-item label="上报时间"><span class="font-mono" style="font-size:13px">{{ formatTime(workOrder.reported_at) }}</span></el-descriptions-item>
          <el-descriptions-item label="执行人">{{ workOrder.assigned_to_name ?? '未分配' }}</el-descriptions-item>
          <el-descriptions-item label="设备">{{ workOrder.device_name ?? '无' }}</el-descriptions-item>
          <el-descriptions-item label="位置" :span="2">{{ workOrder.location ?? '未指定' }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ workOrder.description }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card class="info-card">
        <template #header><span>操作</span></template>
        <el-space>
          <el-button v-if="workOrder.status === 'draft'" type="primary" @click="handleAction('submit')">提交</el-button>
          <el-button v-if="workOrder.status === 'pending'" type="primary" @click="handleAction('assign')">分配</el-button>
          <el-button v-if="workOrder.status === 'assigned'" type="primary" @click="handleAction('start')">开始处理</el-button>
          <el-button v-if="workOrder.status === 'in_progress'" type="primary" @click="handleAction('submit-review')">提交审核</el-button>
          <el-button v-if="workOrder.status === 'pending_review'" type="success" @click="handleAction('approve')">审核通过</el-button>
          <el-button v-if="workOrder.status === 'completed'" type="primary" @click="handleAction('close')">关闭</el-button>
          <el-button v-if="['draft','pending','assigned'].includes(workOrder.status)" type="danger" @click="handleAction('cancel')">取消</el-button>
        </el-space>
      </el-card>

      <el-card v-if="workOrder.details?.length" class="info-card">
        <template #header><span>处理步骤</span></template>
        <el-timeline>
          <el-timeline-item v-for="step in workOrder.details" :key="step.id" :timestamp="step.created_at ? formatTime(step.created_at) : ''" placement="top">
            <h4 style="color: var(--text-primary)">{{ step.step_number }}. {{ step.step_title }}</h4>
            <p v-if="step.step_description" style="color: var(--text-secondary)">{{ step.step_description }}</p>
            <p v-if="step.findings" style="color: var(--text-secondary)"><strong>发现：</strong>{{ step.findings }}</p>
            <p v-if="step.actions_taken" style="color: var(--text-secondary)"><strong>措施：</strong>{{ step.actions_taken }}</p>
          </el-timeline-item>
        </el-timeline>
      </el-card>

      <el-card v-if="workOrder.status_history?.length" class="info-card">
        <template #header><span>状态历史</span></template>
        <el-timeline>
          <el-timeline-item v-for="h in workOrder.status_history" :key="h.id" :timestamp="formatTime(h.changed_at)" placement="top">
            <span style="color: var(--text-primary)">{{ getStatusLabel(h.old_status as any) }} → {{ getStatusLabel(h.new_status as any) }}</span>
            <span class="history-by"> ({{ h.changed_by_name }})</span>
            <p v-if="h.change_notes" class="history-notes">{{ h.change_notes }}</p>
          </el-timeline-item>
        </el-timeline>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getWorkOrder, submitWorkOrder, startWorkOrder, submitReview, approveWorkOrder, closeWorkOrder, cancelWorkOrder, assignWorkOrder } from '@/api/workorder'
import { STATUS_MAP, PRIORITY_MAP, TYPE_MAP } from '@/types/workorder'
import type { WorkOrder, WorkOrderStatus, Priority } from '@/types/workorder'

const route = useRoute()
const router = useRouter()
const workOrder = ref<WorkOrder | null>(null)
const loading = ref(false)
const typeEntries = TYPE_MAP

function getStatusLabel(s: WorkOrderStatus) { return STATUS_MAP[s]?.label ?? s }
function getStatusType(s: WorkOrderStatus) { return STATUS_MAP[s]?.type ?? '' }
function getPriorityLabel(p: Priority) { return PRIORITY_MAP[p]?.label ?? p }
function getPriorityType(p: Priority) { return PRIORITY_MAP[p]?.type ?? '' }
function formatTime(iso: string) { return new Date(iso).toLocaleString('zh-CN') }

async function loadDetail() {
  loading.value = true
  try { workOrder.value = await getWorkOrder(route.params.id as string) as any }
  catch { ElMessage.error('加载工单详情失败') }
  finally { loading.value = false }
}

async function handleAction(action: string) {
  const id = workOrder.value?.id
  if (!id) return
  try {
    switch (action) {
      case 'submit': await submitWorkOrder(id); break
      case 'assign':
        await ElMessageBox.prompt('请输入执行人ID', '分配工单').then(async ({ value }) => {
          await assignWorkOrder(id, { assigned_to: value, assigned_to_name: value })
        }); break
      case 'start': await startWorkOrder(id); break
      case 'submit-review': await submitReview(id, { completion_rate: 100 }); break
      case 'approve': await approveWorkOrder(id); break
      case 'close': await closeWorkOrder(id); break
      case 'cancel':
        await ElMessageBox.prompt('请输入取消原因', '取消工单').then(async ({ value }) => {
          await cancelWorkOrder(id, { cancel_reason: value })
        }); break
    }
    ElMessage.success('操作成功')
    await loadDetail()
  } catch { /* user cancelled or API error */ }
}

onMounted(() => loadDetail())
</script>

<style scoped>
.wo-detail-page { display: flex; flex-direction: column; gap: var(--grid-gap); }
.info-card { margin-top: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.header-tags { display: flex; gap: 8px; }
.history-by { color: var(--text-muted); font-size: 12px; }
.history-notes { color: var(--text-secondary); font-size: 13px; margin-top: 4px; }
</style>
