<template>
  <div class="forbidden-container">
    <div class="forbidden-content">
      <div class="forbidden-code font-mono">403</div>
      <p class="forbidden-text">抱歉，您没有权限访问该页面</p>
      <div class="forbidden-actions">
        <el-button type="primary" @click="router.push('/')">返回首页</el-button>
        <el-button @click="router.back()">返回上一页</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<style scoped>
.forbidden-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}
.forbidden-content {
  text-align: center;
}
.forbidden-code {
  font-size: 72px;
  font-weight: 700;
  color: var(--color-warning);
  line-height: 1;
  margin-bottom: 16px;
}
.forbidden-text {
  font-size: 16px;
  color: var(--text-secondary);
  margin-bottom: 24px;
}
.forbidden-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>
