<template>
  <div class="system-config-view">
    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <!-- 系统参数配置 -->
      <el-tab-pane label="系统参数配置" name="config">
        <div class="toolbar">
          <el-input v-model="configSearch" placeholder="搜索配置键" clearable style="width: 240px" @clear="loadConfigList" @keyup.enter="loadConfigList" />
          <el-select v-model="moduleFilter" placeholder="所属模块" clearable style="width: 160px" @change="loadConfigList">
            <el-option label="SYSTEM" value="SYSTEM" /><el-option label="USER" value="USER" />
            <el-option label="ALERT" value="ALERT" /><el-option label="REPORT" value="REPORT" />
          </el-select>
          <el-button type="primary" @click="showConfigDialog()">新增配置</el-button>
          <el-button @click="handleRefreshCache">刷新缓存</el-button>
        </div>

        <el-table :data="systemStore.configs" v-loading="systemStore.loading" stripe border style="margin-top: 16px">
          <el-table-column prop="config_key" label="配置键" min-width="180">
            <template #default="{ row }"><span class="font-mono">{{ row.config_key }}</span></template>
          </el-table-column>
          <el-table-column prop="config_value" label="配置值" min-width="200" show-overflow-tooltip />
          <el-table-column prop="config_type" label="类型" width="100" />
          <el-table-column prop="module" label="模块" width="120" />
          <el-table-column prop="description" label="说明" min-width="160" show-overflow-tooltip />
          <el-table-column label="系统级" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_system ? 'danger' : 'info'" size="small">{{ row.is_system ? '是' : '否' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="showConfigDialog(row)">编辑</el-button>
              <el-button link type="danger" size="small" :disabled="row.is_system === 1" @click="handleDeleteConfig(row.config_key)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination v-if="systemStore.total > 0" style="margin-top: 16px; justify-content: flex-end" layout="total, prev, pager, next" :total="systemStore.total" :current-page="systemStore.page" :page-size="systemStore.pageSize" @current-change="handleConfigPageChange" />
      </el-tab-pane>

      <!-- 字典数据管理 -->
      <el-tab-pane label="字典数据管理" name="dict">
        <div class="toolbar">
          <el-select v-model="selectedDictType" placeholder="选择字典类型" clearable style="width: 240px" @change="loadDictList">
            <el-option v-for="t in systemStore.dictTypes" :key="t" :label="t" :value="t" />
          </el-select>
          <el-button type="primary" :disabled="!selectedDictType" @click="showDictDialog()">新增字典项</el-button>
        </div>

        <el-table :data="systemStore.dictData" v-loading="systemStore.loading" stripe border style="margin-top: 16px">
          <el-table-column prop="dict_code" label="编码" width="140"><template #default="{ row }"><span class="font-mono">{{ row.dict_code }}</span></template></el-table-column>
          <el-table-column prop="dict_name" label="名称" width="160" />
          <el-table-column prop="dict_value" label="值" width="120" />
          <el-table-column prop="sort_order" label="排序" width="80" align="center" />
          <el-table-column label="状态" width="80" align="center">
            <template #default="{ row }"><el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">{{ row.status === 1 ? '启用' : '禁用' }}</el-tag></template>
          </el-table-column>
          <el-table-column label="系统" width="80" align="center">
            <template #default="{ row }"><el-tag :type="row.is_system ? 'danger' : 'info'" size="small">{{ row.is_system ? '是' : '否' }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="showDictDialog(row)">编辑</el-button>
              <el-button link type="danger" size="small" :disabled="row.is_system === 1" @click="handleDeleteDict(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 系统健康监控 -->
      <el-tab-pane label="系统健康监控" name="health">
        <el-button style="margin-bottom: 16px" @click="loadHealthData">刷新状态</el-button>
        <div v-if="systemStore.health">
          <el-descriptions title="系统状态" :column="2" border>
            <el-descriptions-item label="总体状态">
              <el-tag :type="systemStore.health.status === 'UP' ? 'success' : 'warning'">{{ systemStore.health.status }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="最后刷新时间">{{ systemStore.health.details.lastRefreshTime }}</el-descriptions-item>
            <el-descriptions-item label="配置项数量"><span class="font-mono">{{ systemStore.health.details.configCount }}</span></el-descriptions-item>
            <el-descriptions-item label="字典项数量"><span class="font-mono">{{ systemStore.health.details.dictCount }}</span></el-descriptions-item>
          </el-descriptions>

          <el-table :data="healthComponents" border stripe style="margin-top: 16px">
            <el-table-column prop="name" label="组件" width="200" />
            <el-table-column label="状态" width="120">
              <template #default="{ row }"><el-tag :type="row.status === 'UP' ? 'success' : 'danger'">{{ row.status }}</el-tag></template>
            </el-table-column>
          </el-table>
        </div>
        <el-empty v-else description="点击刷新获取系统状态" />
      </el-tab-pane>
    </el-tabs>

    <!-- Config Dialog -->
    <el-dialog v-model="configDialogVisible" :title="editingConfig ? '编辑配置' : '新增配置'" width="520px">
      <el-form :model="configForm" label-width="100px">
        <el-form-item label="配置键" required><el-input v-model="configForm.config_key" :disabled="!!editingConfig" placeholder="如：system.timeout" /></el-form-item>
        <el-form-item label="配置值"><el-input v-model="configForm.config_value" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="配置类型">
          <el-select v-model="configForm.config_type" style="width: 100%">
            <el-option label="字符串" value="STRING" /><el-option label="数字" value="NUMBER" />
            <el-option label="布尔值" value="BOOLEAN" /><el-option label="JSON" value="JSON" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属模块">
          <el-select v-model="configForm.module" style="width: 100%">
            <el-option label="SYSTEM" value="SYSTEM" /><el-option label="USER" value="USER" />
            <el-option label="ALERT" value="ALERT" /><el-option label="REPORT" value="REPORT" />
          </el-select>
        </el-form-item>
        <el-form-item label="说明"><el-input v-model="configForm.description" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="configDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveConfig">保存</el-button>
      </template>
    </el-dialog>

    <!-- Dict Dialog -->
    <el-dialog v-model="dictDialogVisible" :title="editingDict ? '编辑字典项' : '新增字典项'" width="480px">
      <el-form :model="dictForm" label-width="80px">
        <el-form-item label="字典类型" required><el-input v-model="dictForm.dict_type" :disabled="!!editingDict" /></el-form-item>
        <el-form-item label="编码" required><el-input v-model="dictForm.dict_code" :disabled="!!editingDict" /></el-form-item>
        <el-form-item label="名称" required><el-input v-model="dictForm.dict_name" /></el-form-item>
        <el-form-item label="值"><el-input v-model="dictForm.dict_value" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="dictForm.sort_order" :min="0" /></el-form-item>
        <el-form-item label="状态"><el-switch v-model="dictForm.status" :active-value="1" :inactive-value="0" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="dictForm.remark" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dictDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveDict">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useSystemStore } from '@/stores/system'
import { createConfig, updateConfig, deleteConfig, refreshConfigCache, createDictData, updateDictData, deleteDictData } from '@/api/system'
import type { SysConfig, SysDict } from '@/types/system'

const systemStore = useSystemStore()
const activeTab = ref('config')
const configSearch = ref('')
const moduleFilter = ref('')

const configDialogVisible = ref(false)
const editingConfig = ref<SysConfig | null>(null)
const configForm = ref({ config_key: '', config_value: '', config_type: 'STRING', module: 'SYSTEM', description: '' })

const selectedDictType = ref('')
const dictDialogVisible = ref(false)
const editingDict = ref<SysDict | null>(null)
const dictForm = ref({ dict_type: '', dict_code: '', dict_name: '', dict_value: '', sort_order: 0, status: 1, remark: '' })

const healthComponents = computed(() => {
  if (!systemStore.health) return []
  const c = systemStore.health.components
  return [
    { name: 'MySQL 数据库', status: c.database },
    { name: 'Redis 缓存', status: c.redis },
    { name: 'MinIO 文件存储', status: c.minio },
  ]
})

function handleTabChange(tab: string) {
  if (tab === 'config') loadConfigList()
  else if (tab === 'dict') systemStore.loadDictTypes()
  else if (tab === 'health') loadHealthData()
}

async function loadConfigList() {
  await systemStore.loadConfigs({ page: systemStore.page, size: systemStore.pageSize, module: moduleFilter.value || undefined, configKey: configSearch.value || undefined })
}
function handleConfigPageChange(p: number) { systemStore.page = p; loadConfigList() }

function showConfigDialog(row?: SysConfig) {
  editingConfig.value = row ?? null
  configForm.value = row
    ? { config_key: row.config_key, config_value: row.config_value ?? '', config_type: row.config_type, module: row.module, description: row.description ?? '' }
    : { config_key: '', config_value: '', config_type: 'STRING', module: 'SYSTEM', description: '' }
  configDialogVisible.value = true
}

async function handleSaveConfig() {
  try {
    if (editingConfig.value) {
      await updateConfig(configForm.value.config_key, { config_value: configForm.value.config_value, config_type: configForm.value.config_type, module: configForm.value.module, description: configForm.value.description })
      ElMessage.success('配置更新成功')
    } else {
      await createConfig(configForm.value)
      ElMessage.success('配置创建成功')
    }
    configDialogVisible.value = false; loadConfigList()
  } catch { /* handled */ }
}

async function handleDeleteConfig(key: string) {
  await ElMessageBox.confirm('确定删除该配置项？', '提示', { type: 'warning' })
  try { await deleteConfig(key); ElMessage.success('删除成功'); loadConfigList() } catch { /* handled */ }
}

async function handleRefreshCache() {
  try { await refreshConfigCache(); ElMessage.success('缓存刷新成功') } catch { /* handled */ }
}

async function loadDictList() { if (selectedDictType.value) await systemStore.loadDictData(selectedDictType.value) }

function showDictDialog(row?: SysDict) {
  editingDict.value = row ?? null
  dictForm.value = row
    ? { dict_type: row.dict_type, dict_code: row.dict_code, dict_name: row.dict_name, dict_value: row.dict_value ?? '', sort_order: row.sort_order, status: row.status, remark: row.remark ?? '' }
    : { dict_type: selectedDictType.value, dict_code: '', dict_name: '', dict_value: '', sort_order: 0, status: 1, remark: '' }
  dictDialogVisible.value = true
}

async function handleSaveDict() {
  try {
    if (editingDict.value) {
      await updateDictData(editingDict.value.id, { dict_name: dictForm.value.dict_name, dict_value: dictForm.value.dict_value, sort_order: dictForm.value.sort_order, status: dictForm.value.status, remark: dictForm.value.remark })
      ElMessage.success('字典项更新成功')
    } else {
      await createDictData(dictForm.value)
      ElMessage.success('字典项创建成功')
    }
    dictDialogVisible.value = false; loadDictList()
  } catch { /* handled */ }
}

async function handleDeleteDict(id: number) {
  await ElMessageBox.confirm('确定删除该字典项？', '提示', { type: 'warning' })
  try { await deleteDictData(id); ElMessage.success('删除成功'); loadDictList() } catch { /* handled */ }
}

async function loadHealthData() { await systemStore.loadHealth() }

onMounted(() => { loadConfigList() })
</script>

<style scoped>
.system-config-view { padding: 0; }
.toolbar { display: flex; align-items: center; gap: 12px; }
</style>
