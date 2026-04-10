<template>
  <div class="report-view">
    <div class="report-header">
      <el-radio-group v-model="period" @change="handlePeriodChange" size="small">
        <el-radio-button value="today">今日</el-radio-button>
        <el-radio-button value="week">本周</el-radio-button>
        <el-radio-button value="month">本月</el-radio-button>
        <el-radio-button value="quarter">本季</el-radio-button>
        <el-radio-button value="year">本年</el-radio-button>
      </el-radio-group>
    </div>

    <div class="kpi-grid">
      <div v-for="item in kpiItems" :key="item.key" class="kpi-card">
        <div class="kpi-icon-wrap" :style="{ background: item.iconBg }">
          <el-icon :size="20" :color="item.color"><component :is="item.icon" /></el-icon>
        </div>
        <div class="kpi-body">
          <div class="kpi-value font-mono" :style="{ color: item.color }">{{ item.value }}</div>
          <div class="kpi-label">{{ item.label }}</div>
        </div>
      </div>
    </div>

    <div class="chart-grid">
      <el-card><template #header><span>设备状态分布</span></template><v-chart :option="devicePieOption" style="height:300px" autoresize /></el-card>
      <el-card><template #header><span>工单类型统计</span></template><v-chart :option="workorderBarOption" style="height:300px" autoresize /></el-card>
    </div>
    <div class="chart-grid">
      <el-card><template #header><span>设备类型可用率</span></template><v-chart :option="deviceTypeBarOption" style="height:300px" autoresize /></el-card>
      <el-card><template #header><span>工单优先级分布</span></template><v-chart :option="priorityPieOption" style="height:300px" autoresize /></el-card>
    </div>

    <el-card>
      <template #header><span>报表导出</span></template>
      <div class="export-row">
        <el-select v-model="exportCategory" placeholder="选择报表类型" style="width:200px">
          <el-option label="设备运行统计" value="device" /><el-option label="工单统计" value="workorder" /><el-option label="巡检统计" value="inspection" />
        </el-select>
        <el-select v-model="exportFormat" placeholder="导出格式" style="width:160px">
          <el-option label="Excel (.xlsx)" value="excel" /><el-option label="CSV (.csv)" value="csv" />
        </el-select>
        <el-button type="primary" @click="handleExport" :loading="exporting">导出报表</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart, BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useReportStore } from '@/stores/report'
import { exportReport, getReportTemplates } from '@/api/report'
import type { DashboardKPI } from '@/types/report'
import { WORK_ORDER_TYPE_MAP, PRIORITY_MAP } from '@/types/report'

use([PieChart, BarChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer])

const store = useReportStore()
const period = ref('month')
const exportCategory = ref('device')
const exportFormat = ref('excel')
const exporting = ref(false)
const templates = ref<any[]>([])

const emptyKPI: DashboardKPI = { device_online_rate: 0, workorder_completion_rate: 0, inspection_completion_rate: 0, active_alerts: 0 }
const kpi = computed(() => store.dashboard?.kpi ?? emptyKPI)
function formatPercent(val: number) { return `${val.toFixed(1)}%` }

const kpiItems = computed(() => [
  { key: 'online', label: '设备在线率', value: formatPercent(kpi.value.device_online_rate), icon: 'Monitor', color: '#0891B2', iconBg: 'rgba(8,145,178,0.08)' },
  { key: 'wo', label: '工单完成率', value: formatPercent(kpi.value.workorder_completion_rate), icon: 'Document', color: '#10B981', iconBg: 'rgba(16,185,129,0.08)' },
  { key: 'insp', label: '巡检完成率', value: formatPercent(kpi.value.inspection_completion_rate), icon: 'Search', color: '#F59E0B', iconBg: 'rgba(245,158,11,0.08)' },
  { key: 'alert', label: '活跃告警', value: `${kpi.value.active_alerts}`, icon: 'Bell', color: '#EF4444', iconBg: 'rgba(239,68,68,0.08)' },
])

const devicePieOption = computed(() => {
  const s = store.dashboard?.device_stats?.summary; if (!s) return {}
  return {
    tooltip: { trigger: 'item' }, legend: { bottom: 0 },
    series: [{ type: 'pie', radius: ['45%', '72%'],
      data: [
        { value: s.online_devices, name: '在线', itemStyle: { color: '#10B981' } },
        { value: s.offline_devices, name: '离线', itemStyle: { color: '#94A3B8' } },
        { value: s.fault_devices, name: '故障', itemStyle: { color: '#EF4444' } },
        { value: s.maintenance_devices, name: '维护', itemStyle: { color: '#F59E0B' } },
      ].filter(d => d.value > 0),
      label: { formatter: '{b}: {c} ({d}%)' },
    }],
  }
})

const workorderBarOption = computed(() => {
  const types = store.dashboard?.workorder_stats?.by_type ?? []; if (!types.length) return {}
  return {
    tooltip: { trigger: 'axis' }, grid: { left: 60, right: 20, bottom: 30, top: 20 },
    xAxis: { type: 'category', data: types.map(t => WORK_ORDER_TYPE_MAP[t.work_order_type] ?? t.work_order_type) },
    yAxis: { type: 'value' },
    series: [
      { name: '总数', type: 'bar', data: types.map(t => t.count), itemStyle: { color: '#0891B2', borderRadius: [6, 6, 0, 0] } },
      { name: '已完成', type: 'bar', data: types.map(t => t.completed), itemStyle: { color: '#10B981', borderRadius: [6, 6, 0, 0] } },
    ],
  }
})

const deviceTypeBarOption = computed(() => {
  const types = store.dashboard?.device_stats?.by_device_type ?? []; if (!types.length) return {}
  return {
    tooltip: { trigger: 'axis' }, grid: { left: 60, right: 20, bottom: 30, top: 20 },
    xAxis: { type: 'category', data: types.map(t => t.device_type_name) },
    yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
    series: [{ name: '可用率', type: 'bar', data: types.map(t => t.availability), itemStyle: { color: '#22D3EE', borderRadius: [6, 6, 0, 0] }, label: { show: true, position: 'top', formatter: '{c}%' } }],
  }
})

const priorityPieOption = computed(() => {
  const priorities = store.dashboard?.workorder_stats?.by_priority ?? []; if (!priorities.length) return {}
  const colorMap: Record<string, string> = { low: '#10B981', medium: '#0891B2', high: '#F59E0B', emergency: '#EF4444' }
  return {
    tooltip: { trigger: 'item' }, legend: { bottom: 0 },
    series: [{ type: 'pie', radius: ['45%', '72%'],
      data: priorities.map(p => ({ value: p.count, name: PRIORITY_MAP[p.priority]?.label ?? p.priority, itemStyle: { color: colorMap[p.priority] ?? '#94A3B8' } })),
      label: { formatter: '{b}: {c}' },
    }],
  }
})

function handlePeriodChange() { store.period = period.value; store.loadDashboard() }

async function handleExport() {
  exporting.value = true
  try {
    const categoryMap: Record<string, string> = { device: '设备', workorder: '运维', inspection: '运营' }
    const cat = categoryMap[exportCategory.value] || exportCategory.value
    let templateId = templates.value.find((t: any) => t.category === cat)?.id
    if (!templateId && templates.value.length > 0) templateId = templates.value[0].id
    if (!templateId) { ElMessage.warning('未找到可用的报表模板'); return }
    await exportReport(templateId, { parameters: { category: exportCategory.value, period: period.value }, format: exportFormat.value })
    ElMessage.success('导出任务已提交，请稍后查看')
  } catch { ElMessage.error('导出失败') } finally { exporting.value = false }
}

onMounted(async () => {
  store.loadDashboard()
  try { const res: any = await getReportTemplates({ is_active: true }); templates.value = res?.items ?? [] } catch {}
})
</script>

<style scoped>
.report-view { display: flex; flex-direction: column; gap: var(--grid-gap); }
.report-header { display: flex; justify-content: flex-end; }
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--grid-gap); }
.kpi-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: var(--card-radius); padding: 20px; display: flex; align-items: center; gap: 16px; box-shadow: var(--shadow-card); }
.kpi-icon-wrap { width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.kpi-body { flex: 1; }
.kpi-value { font-size: 24px; font-weight: 700; line-height: 1.2; }
.kpi-label { font-size: 13px; color: var(--text-muted); margin-top: 2px; }
.chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--grid-gap); }
.export-row { display: flex; gap: 12px; align-items: center; }
@media (max-width: 1024px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } .chart-grid { grid-template-columns: 1fr; } }
</style>
