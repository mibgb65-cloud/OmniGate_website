<script setup>
import TotpCodeTool from '@/components/security/TotpCodeTool.vue'
import TotpBatchTool from '@/components/security/TotpBatchTool.vue'
</script>

<template>
  <div class="tool-page">
    <section class="tool-hero">
      <div>
        <h1>2FA 聚合工具</h1>
        <p>集中生成 6 位 TOTP 验证码，支持手动输入密钥或粘贴账号密钥。</p>
      </div>
    </section>

    <section class="tool-grid">
      <div class="tool-stack">
        <article class="tool-card">
          <TotpCodeTool :show-use-account-secret-button="false" />
        </article>

        <article class="tool-card">
          <TotpBatchTool />
        </article>
      </div>

      <article class="tool-card tips-card">
        <h3>使用说明</h3>
        <ul>
          <li>仅支持 Base32 格式密钥（可包含空格/短横线）。</li>
          <li>验证码默认每 30 秒自动更新一次。</li>
          <li>可直接粘贴账号密钥进行计算。</li>
          <li>批量模式支持每行 1 个密钥，自动生成对应验证码。</li>
          <li>批量复制会按“行号 + 验证码”输出，便于逐条对应。</li>
          <li>本工具仅在浏览器本地计算，不会上传密钥。</li>
        </ul>
      </article>
    </section>
  </div>
</template>

<style scoped>
.tool-page {
  display: grid;
  gap: 16px;
}

.tool-hero {
  border-radius: 14px;
  padding: 20px;
  background:
    radial-gradient(circle at 86% 20%, rgba(14, 165, 233, 0.2), transparent 34%),
    linear-gradient(136deg, #162231 0%, #1e2f41 100%);
  color: #f7fbff;
}

.tool-hero h1 {
  margin: 0;
  font-size: 1.3rem;
}

.tool-hero p {
  margin: 8px 0 0;
  color: rgba(247, 251, 255, 0.86);
}

.tool-grid {
  display: grid;
  grid-template-columns: 1.4fr 0.6fr;
  gap: 14px;
}

.tool-stack {
  display: grid;
  gap: 14px;
}

.tool-card {
  border-radius: 12px;
  border: 1px solid rgba(23, 37, 48, 0.08);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  background: #ffffff;
  padding: 18px;
}

.tips-card h3 {
  margin: 0 0 10px;
  color: var(--og-slate-900);
  font-size: 1rem;
}

.tips-card ul {
  margin: 0;
  padding-left: 18px;
  color: var(--og-slate-600);
  display: grid;
  gap: 8px;
  line-height: 1.5;
}

@media (max-width: 980px) {
  .tool-grid {
    grid-template-columns: 1fr;
  }
}
</style>
