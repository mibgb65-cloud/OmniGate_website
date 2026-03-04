<template>
  <el-card shadow="never" class="placeholder-card">
    <h2>ChatGPT 模块</h2>
    <p>
      后端账号管理接口已就绪（含单条 CRUD 与批量操作）。
      当前页面仍为占位状态，后续可直接接入 `src/api/chatgpt.js` 完成业务联调。
    </p>
  </el-card>
</template>

<style scoped>
.placeholder-card {
  border-radius: 16px;
  background: var(--og-surface);
  backdrop-filter: blur(8px);
  min-height: 180px;
}

h2 {
  margin: 4px 0 8px;
  font-family: 'Space Grotesk', sans-serif;
  color: var(--og-slate-900);
}

p {
  margin: 0;
  line-height: 1.8;
  color: var(--og-slate-600);
  max-width: 760px;
}
</style>
