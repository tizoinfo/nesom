<template>
  <div class="sparepart-page">
    <el-alert
      v-if="store.alerts.length > 0"
      :title="`${store.alerts.length} 条库存预警`"
      type="warning"
      show-icon
      :closable="false"
      style="cursor: pointer"
      @click="showAlerts = true"
    />

    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索备件名称/编码/规格" clearable style="width: 240px" @clear="handleSearch" @keyup.enter="handleSearch" />
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 120px" @change="handleSearch">
        <el-option label="启用" value="active" />
        <el-option label="停用" value="inactive" />
        <el-option label="淘汰" value="obsolete" />
      </el-select>
      <el-select v-model="categoryFilter" placeholder="分类" clearable style="width: 160px" @change="handleSearch">
        <el-option v-for="cat in store.categories" :key="cat.id" :label="cat.category_name" :value="cat.id" />
      </el-select>
      <el-checkbox v-model="lowStockOnly" @change="handleSearch">仅低库存</el-checkbox>
      <el-button type="primary" @click="handleSearch">查询</el-button>
      <el-button type="warning" @click="showAlerts = true">预警 ({{ store.alerts.length }})</el-button>
    </div>

    <el-card>
      <el-table :data="store.spareParts" v-loading="store.loading" stripe>
        <el-table-column prop="spare_part_code" label="编码" width="160">
          <template #default="{ row }"><span class="font-mono">{{ row.spare_part_code }}</span></template>
        </el-table-column>
        <el-table-column prop="spare_part_name" label="名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="specification" label="规格" width="140" show-overflow-tooltip />
        <el-table-column prop="brand" label="品牌" width="100" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="当前库存" width="100" align="right">
          <template #default="{ row }">
            <span class="font-mono" :class="{ 'text-danger': isLowStock(row) }">{{ row.current_stock }}</span>
          </template>
        </el-table-column>
        <el-table-column label="可用库存" width="100" align="right">
          <template #default="{ row }"><span class="font-mono">{{ row.available_stock }}</span></template>
        </el-table-column>
        <el-table-column label="预留" width="80" align="right">
          <template #default="{ row }"><span class="font-mono">{{ row.reserved_stock }}</span></template>
        </el-table-column>
        <el-table-column label="安全库存" width="100" align="right">
          <template #default="{ row }"><span class="font-mono">{{ row.safety_stock_level ?? '-' }}</span></template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openReceive(row)">入库</el-button>
            <el-button link type="warning" size="small" @click="openIssue(row)">出库</el-button>
          </template>
        </el-table-column>
      </el-table>

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

    <!-- Receive Dialog -->
    <el-dialog v-model="showReceive" title="入库操作" width="500px" destroy-on-close>
      <el-form :model="receiveForm" label-width="80px">
        <el-form-item label="备件"><el-input :model-value="receiveForm.spare_part_name" disabled /></el-form-item>
        <el-form-item label="数量" required><el-input-number v-model="receiveForm.quantity" :min="1" :precision="0" /></el-form-item>
        <el-form-item label="单价"><el-input-number v-model="receiveForm.unit_price" :min="0" :precision="2" /></el-form-item>
        <el-form-item label="批次号"><el-input v-model="receiveForm.batch_no" placeholder="可选" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="receiveForm.remarks" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showReceive = false">取消</el-button>
        <el-button type="primary" @click="handleReceive" :loading="submitting">确认入库</el-button>
      </template>
    </el-dialog>

    <!-- Issue Dialog -->
    <el-dialog v-model="showIssue" title="出库操作" width="500px" destroy-on-close>
      <el-form :model="issueForm" label-width="80px">
        <el-form-item label="备件"><el-input :model-value="issueForm.spare_part_name" disabled /></el-form-item>
        <el-form-item label="可用库存"><el-input :model-value="issueForm.available_stock" disabled /></el-form-item>
        <el-form-item label="数量" required><el-input-number v-model="issueForm.quantity" :min="1" :max="issueForm.available_stock" :precision="0" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="issueForm.remarks" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showIssue = false">取消</el-button>
        <el-button type="warning" @click="handleIssue" :loading="submitting">确认出库</el-button>
      </template>
    </el-dialog>

    <!-- Alerts Drawer -->
    <el-drawer v-model="showAlerts" title="库存预警" size="450px">
      <div v-if="store.alerts.length === 0" style="padding: 40px 0"><el-empty description="暂无预警" /></div>
      <div v-else class="alert-list">
        <div v-for="(alert, idx) in store.alerts" :key="idx" class="alert-item">
          <div class="alert-header">
            <el-tag :type="getSeverityType(alert.severity)" size="small">{{ getSeverityLabel(alert.severity) }}</el-tag>
            <el-tag size="small" type="info">{{ alert.alert_type === 'low_stock' ? '低库存' : '近效期' }}</el-tag>
          </div>
          <div class="alert-name">{{ alert.spare_part_name }}</div>
          <div class="alert-msg">{{ alert.alert_message }}</div>
          <div class="alert-action">{{ alert.suggested_action }}</div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useSparePartStore } from '@/stores/sparepart'
import { useUserStore } from '@/stores/user'
import { receiveStock, issueStock } from '@/api/sparepart'
import { STATUS_MAP, SEVERITY_MAP } from '@/types/sparepart'
import type { SparePart, SparePartStatus, AlertSeverity } from '@/types/sparepart'
import request from '@/utils/request'

const store = useSparePartStore()
const userStore = useUserStore()

const keyword = ref('')
const statusFilter = ref('')
const categoryFilter = ref('')
const lowStockOnly = ref(false)
const currentPage = ref(1)
const currentPageSize = ref(20)
const submitting = ref(false)
const defaultWarehouseId = ref('')

const showReceive = ref(false)
const showIssue = ref(false)
const showAlerts = ref(false)

const receiveForm = ref({ spare_part_id: '', spare_part_name: '', quantity: 1, unit_price: 0, batch_no: '', remarks: '' })
const issueForm = ref({ spare_part_id: '', spare_part_name: '', available_stock: 0, quantity: 1, remarks: '' })

function getStatusLabel(s: SparePartStatus) { return STATUS_MAP[s]?.label ?? s }
function getStatusType(s: SparePartStatus) { return STATUS_MAP[s]?.type ?? '' }
function getSeverityLabel(s: AlertSeverity) { return SEVERITY_MAP[s]?.label ?? s }
function getSeverityType(s: AlertSeverity) { return SEVERITY_MAP[s]?.type ?? '' }
function isLowStock(row: SparePart) { return row.safety_stock_level != null && row.available_stock < row.safety_stock_level }

function handleSearch() { currentPage.value = 1; fetchData() }
function handlePageChange(p: number) { currentPage.value = p; fetchData() }
function handleSizeChange(s: number) { currentPageSize.value = s; currentPage.value = 1; fetchData() }

function fetchData() {
  store.loadSpareParts({
    page: currentPage.value, page_size: currentPageSize.value,
    keyword: keyword.value || undefined, status: statusFilter.value || undefined,
    category_id: categoryFilter.value || undefined, low_stock_only: lowStockOnly.value || undefined,
  })
}

function openReceive(row: SparePart) {
  receiveForm.value = { spare_part_id: row.id, spare_part_name: `${row.spare_part_code} - ${row.spare_part_name}`, quantity: 1, unit_price: row.last_purchase_price ?? 0, batch_no: '', remarks: '' }
  showReceive.value = true
}

function openIssue(row: SparePart) {
  issueForm.value = { spare_part_id: row.id, spare_part_name: `${row.spare_part_code} - ${row.spare_part_name}`, available_stock: row.available_stock, quantity: 1, remarks: '' }
  showIssue.value = true
}

async function handleReceive() {
  if (receiveForm.value.quantity <= 0) { ElMessage.warning('请输入有效数量'); return }
  if (!defaultWarehouseId.value) { ElMessage.warning('未找到仓库信息'); return }
  submitting.value = true
  try {
    await receiveStock({
      transaction_type: 'purchase_in',
      operator_id: userStore.userInfo?.id ?? 'system',
      operator_name: (userStore.userInfo as any)?.real_name ?? userStore.userInfo?.username ?? '系统',
      items: [{ spare_part_id: receiveForm.value.spare_part_id, warehouse_id: defaultWarehouseId.value, quantity: receiveForm.value.quantity, unit_price: receiveForm.value.unit_price, batch_no: receiveForm.value.batch_no || undefined }],
      remarks: receiveForm.value.remarks || undefined,
    })
    ElMessage.success('入库成功'); showReceive.value = false; fetchData(); store.loadAlerts()
  } catch { ElMessage.error('入库失败') } finally { submitting.value = false }
}

async function handleIssue() {
  if (issueForm.value.quantity <= 0) { ElMessage.warning('请输入有效数量'); return }
  if (!defaultWarehouseId.value) { ElMessage.warning('未找到仓库信息'); return }
  submitting.value = true
  try {
    await issueStock({
      transaction_type: 'issue_out',
      operator_id: userStore.userInfo?.id ?? 'system',
      operator_name: (userStore.userInfo as any)?.real_name ?? userStore.userInfo?.username ?? '系统',
      items: [{ spare_part_id: issueForm.value.spare_part_id, warehouse_id: defaultWarehouseId.value, quantity: issueForm.value.quantity }],
      remarks: issueForm.value.remarks || undefined,
    })
    ElMessage.success('出库成功'); showIssue.value = false; fetchData(); store.loadAlerts()
  } catch { ElMessage.error('出库失败') } finally { submitting.value = false }
}

onMounted(async () => {
  fetchData(); store.loadCategories(); store.loadAlerts()
  try {
    const warehouses: any = await request.get('/v1/warehouses')
    if (Array.isArray(warehouses) && warehouses.length > 0) defaultWarehouseId.value = warehouses[0].id
  } catch { /* ignore */ }
})
</script>

<style scoped>
.sparepart-page { display: flex; flex-direction: column; gap: var(--grid-gap); }
.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.pagination { margin-top: 16px; justify-content: flex-end; }

.alert-list { display: flex; flex-direction: column; gap: 12px; }
.alert-item {
  background: var(--bg-elevated);
  border: 1px solid var(--border-light);
  border-radius: 10px;
  padding: 14px;
}
.alert-header { display: flex; gap: 8px; margin-bottom: 8px; }
.alert-name { font-weight: 600; font-size: 14px; color: var(--text-primary); margin-bottom: 4px; }
.alert-msg { color: var(--text-secondary); font-size: 13px; margin-bottom: 4px; }
.alert-action { color: var(--color-primary); font-size: 12px; }
</style>
