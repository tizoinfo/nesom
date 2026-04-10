<template>
  <div class="device-detail" v-loading="loading">
    <el-page-header @back="router.back()">
      <template #content>
        <span>{{ device?.device_name ?? '设备详情' }}</span>
        <el-tag v-if="device" :type="getStatusType(device.status)" size="small" style="margin-left: 8px">
          {{ getStatusLabel(device.status) }}
        </el-tag>
      </template>
    </el-page-header>

    <template v-if="device">
      <el-tabs v-model="activeTab" class="detail-tabs">
        <!-- Overview Tab -->
        <el-tab-pane label="概览" name="overview">
          <div class="overview-grid">
            <el-card>
              <template #header><span>基本信息</span></template>
              <el-descriptions :column="2" border size="small">
                <el-descriptions-item label="设备编码"><span class="font-mono">{{ device.device_code }}</span></el-descriptions-item>
                <el-descriptions-item label="设备名称">{{ device.device_name }}</el-descriptions-item>
                <el-descriptions-item label="设备类型">{{ device.device_type?.type_name ?? '--' }}</el-descriptions-item>
                <el-descriptions-item label="制造商">{{ device.manufacturer ?? '--' }}</el-descriptions-item>
                <el-descriptions-item label="型号">{{ device.model ?? '--' }}</el-descriptions-item>
                <el-descriptions-item label="序列号"><span class="font-mono">{{ device.serial_number ?? '--' }}</span></el-descriptions-item>
                <el-descriptions-item label="额定功率"><span class="font-mono">{{ device.rated_power ? device.rated_power + ' kW' : '--' }}</span></el-descriptions-item>
                <el-descriptions-item label="健康评分">
                  <span class="font-mono" :style="{ color: getScoreColor(device.health_score), fontWeight: 'bold' }">
                    {{ device.health_score ?? '--' }}
                  </span>
                </el-descriptions-item>
                <el-descriptions-item label="负责人">{{ device.responsible_person_name ?? '--' }}</el-descriptions-item>
                <el-descriptions-item label="位置">{{ device.location_description ?? '--' }}</el-descriptions-item>
              </el-descriptions>
            </el-card>

            <el-card>
              <template #header><span>实时数据</span></template>
              <div v-if="realtimeMetrics.length" class="metrics-grid">
                <div v-for="m in realtimeMetrics" :key="m.metric_type" class="metric-item">
                  <div class="metric-value font-mono">{{ m.metric_value }}</div>
                  <div class="metric-label">{{ m.metric_type }}</div>
                  <div class="metric-unit">{{ m.metric_unit }}</div>
                </div>
              </div>
              <el-empty v-else description="暂无实时数据" :image-size="60" />
            </el-card>
          </div>
        </el-tab-pane>

        <!-- Alerts Tab -->
        <el-tab-pane label="告警记录" name="alerts">
          <el-table :data="alerts" v-loading="alertsLoading" stripe>
            <el-table-column label="级别" width="80">
              <template #default="{ row }">
                <el-tag :type="getAlertType(row.alert_level)" size="small">{{ getAlertLabel(row.alert_level) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="alert_title" label="标题" min-width="180" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }"><el-tag size="small">{{ row.status }}</el-tag></template>
            </el-table-column>
            <el-table-column label="触发时间" width="170">
              <template #default="{ row }"><span class="font-mono" style="font-size:12px">{{ formatTime(row.start_time) }}</span></template>
            </el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button v-if="row.status === 'active'" link type="primary" size="small" @click="handleAcknowledge(row.id)">确认</el-button>
                <el-button v-if="row.status === 'active' || row.status === 'acknowledged'" link type="success" size="small" @click="handleResolve(row.id)">解决</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- History Tab -->
        <el-tab-pane label="历史数据" name="history">
          <div class="history-toolbar">
            <el-input v-model="historyMetricType" placeholder="指标类型 (如 voltage)" style="width: 200px" />
            <el-date-picker
              v-model="historyRange"
              type="datetimerange"
              range-separator="至"
              start-placeholder="开始时间"
              end-placeholder="结束时间"
              format="YYYY-MM-DD HH:mm"
              value-format="YYYY-MM-DDTHH:mm:ss"
            />
            <el-button type="primary" @click="fetchHistory">查询</el-button>
          </div>
          <div ref="chartRef" class="history-chart" />
          <el-empty v-if="!historyData.length && !historyLoading" description="请选择指标和时间范围查询" />
        </el-tab-pane>
      </el-tabs>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import { getDevice, getRealtimeMetrics, getDeviceAlerts, acknowledgeAlert, resolveAlert, getHistoricalMetrics } from '@/api/device'
import { STATUS_MAP, ALERT_LEVEL_MAP } from '@/types/device'
import type { Device, DeviceMetric, DeviceAlert, DeviceStatus, AlertLevel } from '@/types/device'

const route = useRoute()
const router = useRouter()
const deviceId = route.params.id as string

const loading = ref(false)
const device = ref<Device | null>(null)
const activeTab = ref('overview')
const realtimeMetrics = ref<DeviceMetric[]>([])
const alerts = ref<DeviceAlert[]>([])
const alertsLoading = ref(false)
const historyMetricType = ref('voltage')
const historyRange = ref<string[]>([])
const historyData = ref<{ time: string; value: number }[]>([])
const historyLoading = ref(false)
const chartRef = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null

function getStatusLabel(s: DeviceStatus) { return STATUS_MAP[s]?.label ?? s }
function getStatusType(s: DeviceStatus) { return STATUS_MAP[s]?.type ?? '' }
function getScoreColor(score?: number) {
  if (!score) return 'var(--text-muted)'
  if (score >= 90) return '#10B981'
  if (score >= 70) return '#0891B2'
  if (score >= 50) return '#F59E0B'
  return '#EF4444'
}
function getAlertLabel(l: AlertLevel) { return ALERT_LEVEL_MAP[l]?.label ?? l }
function getAlertType(l: AlertLevel) { return ALERT_LEVEL_MAP[l]?.type ?? '' }
function formatTime(iso: string) { return new Date(iso).toLocaleString('zh-CN') }

async function fetchDevice() {
  loading.value = true
  try { device.value = await getDevice(deviceId) as any } finally { loading.value = false }
}

async function fetchRealtime() {
  try {
    const res: any = await getRealtimeMetrics(deviceId)
    realtimeMetrics.value = res?.metrics ?? []
  } catch { /* ignore */ }
}

async function fetchAlerts() {
  alertsLoading.value = true
  try {
    const res: any = await getDeviceAlerts(deviceId, { page: 1, page_size: 50 })
    alerts.value = res?.items ?? []
  } finally { alertsLoading.value = false }
}

async function handleAcknowledge(alertId: number) {
  await acknowledgeAlert(deviceId, alertId)
  ElMessage.success('告警已确认')
  fetchAlerts()
}

async function handleResolve(alertId: number) {
  const { value } = await ElMessageBox.prompt('请输入解决说明', '解决告警', {
    confirmButtonText: '确认', cancelButtonText: '取消',
    inputValidator: (v) => (v && v.trim() ? true : '请输入解决说明'),
  })
  await resolveAlert(deviceId, alertId, value)
  ElMessage.success('告警已解决')
  fetchAlerts()
}

async function fetchHistory() {
  if (!historyMetricType.value || !historyRange.value?.length) {
    ElMessage.warning('请选择指标类型和时间范围')
    return
  }
  historyLoading.value = true
  try {
    const res: any = await getHistoricalMetrics(deviceId, {
      metric_type: historyMetricType.value,
      start_time: historyRange.value[0],
      end_time: historyRange.value[1],
    })
    historyData.value = res?.data ?? []
    await nextTick()
    renderChart()
  } finally { historyLoading.value = false }
}

function renderChart() {
  if (!chartRef.value || !historyData.value.length) return
  if (!chartInstance) chartInstance = echarts.init(chartRef.value)
  chartInstance.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'time', data: historyData.value.map(d => d.time) },
    yAxis: { type: 'value' },
    series: [{
      type: 'line', smooth: true,
      data: historyData.value.map(d => [d.time, d.value]),
      lineStyle: { color: '#0891B2', width: 2 },
      itemStyle: { color: '#0891B2' },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(8,145,178,0.15)' }, { offset: 1, color: 'rgba(8,145,178,0)' }] } },
    }],
  })
}

watch(activeTab, (tab) => { if (tab === 'alerts') fetchAlerts() })
onMounted(() => { fetchDevice(); fetchRealtime() })
</script>

<style scoped>
.device-detail { display: flex; flex-direction: column; gap: var(--grid-gap); }
.detail-tabs { margin-top: 8px; }

.overview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--grid-gap);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
}
.metric-item {
  text-align: center;
  padding: 14px 8px;
  background: var(--bg-hover);
  border-radius: 10px;
  border: 1px solid var(--border-light);
}
.metric-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-primary);
}
.metric-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}
.metric-unit {
  font-size: 11px;
  color: var(--text-muted);
}

.history-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}
.history-chart { width: 100%; height: 350px; }

@media (max-width: 1024px) {
  .overview-grid { grid-template-columns: 1fr; }
}
</style>
