<template>
  <div class="dashboard">
    <!-- KPI Cards -->
    <div class="kpi-grid">
      <div v-for="kpi in kpiCards" :key="kpi.key" class="kpi-card">
        <div class="kpi-icon-wrap" :style="{ background: kpi.iconBg }">
          <el-icon :size="22" :color="kpi.color"><component :is="kpi.icon" /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value font-mono" :style="{ color: kpi.color }">{{ kpi.value }}</div>
          <div class="kpi-label">{{ kpi.label }}</div>
        </div>
      </div>
    </div>

    <!-- Summary Row -->
    <div class="summary-grid">
      <el-card>
        <template #header><span>设备概况</span></template>
        <div class="stat-list">
          <div class="stat-row"><span class="stat-label">设备总数</span><span class="stat-value font-mono">{{ data?.device_stats?.summary?.total_devices ?? 0 }}</span></div>
          <div class="stat-row"><span class="stat-label">在线设备</span><span class="stat-value font-mono text-success">{{ data?.device_stats?.summary?.online_devices ?? 0 }}</span></div>
          <div class="stat-row"><span class="stat-label">离线设备</span><span class="stat-value font-mono text-muted">{{ data?.device_stats?.summary?.offline_devices ?? 0 }}</span></div>
          <div class="stat-row"><span class="stat-label">故障设备</span><span class="stat-value font-mono text-danger">{{ data?.device_stats?.summary?.fault_devices ?? 0 }}</span></div>
          <div class="stat-row"><span class="stat-label">平均OEE</span><span class="stat-value font-mono text-primary-color">{{ data?.device_stats?.summary?.avg_oee ?? 0 }}%</span></div>
        </div>
      </el-card>
      <el-card>
        <template #header><span>工单概况</span></template>
        <div class="stat-list">
          <div class="stat-row"><span class="stat-label">工单总数</span><span class="stat-value font-mono">{{ data?.workorder_stats?.summary?.total_workorders ?? 0 }}</span></div>
          <div class="stat-row"><span class="stat-label">已完成</span><span class="stat-value font-mono text-success">{{ data?.workorder_stats?.summary?.completed_workorders ?? 0 }}</span></div>
          <div class="stat-row"><span class="stat-label">进行中</span><span class="stat-value font-mono text-primary-color">{{ data?.workorder_stats?.summary?.in_progress_workorders ?? 0 }}</span></div>
          <div class="stat-row"><span class="stat-label">待处理</span><span class="stat-value font-mono text-warning">{{ data?.workorder_stats?.summary?.pending_workorders ?? 0 }}</span></div>
          <div class="stat-row"><span class="stat-label">平均耗时</span><span class="stat-value font-mono">{{ data?.workorder_stats?.summary?.avg_completion_hours ? data.workorder_stats.summary.avg_completion_hours.toFixed(1) + 'h' : '--' }}</span></div>
        </div>
      </el-card>
      <el-card>
        <template #header><span>巡检概况</span></template>
        <div class="stat-list">
          <div class="stat-row"><span class="stat-label">任务总数</span><span class="stat-value font-mono">{{ data?.inspection_stats?.total_tasks ?? 0 }}</span></div>
          <div class="stat-row"><span class="stat-label">已完成</span><span class="stat-value font-mono text-success">{{ data?.inspection_stats?.completed_tasks ?? 0 }}</span></div>
          <div class="stat-row"><span class="stat-label">待执行</span><span class="stat-value font-mono text-warning">{{ data?.inspection_stats?.pending_tasks ?? 0 }}</span></div>
          <div class="stat-row"><span class="stat-label">发现问题</span><span class="stat-value font-mono text-danger">{{ data?.inspection_stats?.problem_count ?? 0 }}</span></div>
          <div class="stat-row"><span class="stat-label">完成率</span><span class="stat-value font-mono text-primary-color">{{ data?.inspection_stats?.completion_rate ?? 0 }}%</span></div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import request from '@/utils/request'

const data = ref<any>(null)

function formatPercent(val?: number) { return val != null ? `${val.toFixed(1)}%` : '--' }

const kpiCards = computed(() => [
  { key: 'online', label: '设备在线率', value: formatPercent(data.value?.kpi?.device_online_rate), icon: 'Monitor', color: '#0891B2', iconBg: 'rgba(8,145,178,0.08)' },
  { key: 'workorder', label: '工单完成率', value: formatPercent(data.value?.kpi?.workorder_completion_rate), icon: 'Document', color: '#10B981', iconBg: 'rgba(16,185,129,0.08)' },
  { key: 'inspection', label: '巡检完成率', value: formatPercent(data.value?.kpi?.inspection_completion_rate), icon: 'Search', color: '#F59E0B', iconBg: 'rgba(245,158,11,0.08)' },
  { key: 'alerts', label: '活跃告警', value: `${data.value?.kpi?.active_alerts ?? 0}`, icon: 'Bell', color: '#EF4444', iconBg: 'rgba(239,68,68,0.08)' },
])

onMounted(async () => {
  try { data.value = await request.get('/v1/stats/dashboard', { params: { period: 'month' } }) } catch {}
})
</script>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: var(--grid-gap); }

.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--grid-gap); }

.kpi-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--card-radius);
  padding: 22px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: var(--shadow-card);
  transition: box-shadow var(--transition-normal), transform var(--transition-normal);
  cursor: default;
}
.kpi-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }

.kpi-icon-wrap {
  width: 50px; height: 50px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.kpi-body { flex: 1; min-width: 0; }
.kpi-value { font-size: 26px; font-weight: 700; line-height: 1.2; }
.kpi-label { font-size: 13px; color: var(--text-muted); margin-top: 4px; }

.summary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--grid-gap); }

.stat-list { display: flex; flex-direction: column; }
.stat-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 0; border-bottom: 1px solid var(--border-light);
}
.stat-row:last-child { border-bottom: none; }
.stat-label { font-size: 13px; color: var(--text-secondary); }
.stat-value { font-size: 15px; font-weight: 600; color: var(--text-primary); }

@media (max-width: 1024px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } .summary-grid { grid-template-columns: 1fr; } }
@media (max-width: 640px) { .kpi-grid { grid-template-columns: 1fr; } }
</style>
