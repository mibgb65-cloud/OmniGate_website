<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="not-found">
    <el-card shadow="never" class="not-found-card">
      <h1>404</h1>
      <p>页面不存在或已迁移。</p>
      <el-button type="primary" @click="router.push('/google/accounts')">返回控制台</el-button>
    </el-card>
  </div>
</template>

<style scoped>
.not-found {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
}

.not-found-card {
  width: min(420px, 100%);
  text-align: center;
  border-radius: 16px;
  background: var(--og-surface);
  backdrop-filter: blur(8px);
}

h1 {
  margin: 6px 0 8px;
  font-family: 'Space Grotesk', sans-serif;
  font-size: 2.4rem;
}

p {
  margin: 0 0 16px;
  color: var(--og-slate-600);
}
</style>
