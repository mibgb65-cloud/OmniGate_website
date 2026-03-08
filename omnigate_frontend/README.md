# omnigate_frontend

OmniGate 管理前端，基于 Vue 3 + Vite + Element Plus，负责账号池管理、任务触发、任务状态查看和系统配置维护。

## 已落地页面

- ChatGPT 账号池：`/chatgpt/accounts`
- ChatGPT 账号详情：`/chatgpt/accounts/:id`
- CloudMail 配置中心：`/settings/cloudmail`
- Google / GitHub / ChatGPT 账号详情页凭据复制与导出
- 2FA 工具页：支持单个或多行密钥批量解析验证码

## 本地启动

```sh
npm install
npm run dev
```

默认通过 `VITE_API_BASE_URL` 连接后端。开发环境下如果前后端分开启动，请确认该值已经指向 Spring Boot 服务地址。

## 生产构建

```sh
npm run build
```

## 关键联动说明

### ChatGPT 自动注册

- 页面入口在 ChatGPT 账号池
- 点击“自动注册”后，会调用后端 `POST /api/chatgpt/tasks/batch-register`
- 后端会先检查 CloudMail 与注册邮箱后缀配置是否完整
- 校验通过后才会真正投递 Worker 任务
- 任务结束后，页面会自动刷新账号列表

### CloudMail 配置中心

CloudMail 配置页用于维护 ChatGPT 自动注册所依赖的四项配置：

- CloudMail 登录账号（邮箱）
- CloudMail 登录密码
- CloudMail 登录网址
- ChatGPT 注册邮箱后缀

其中邮箱后缀只填写域名，例如 `example.com`，不要带 `@`。

## 建议联调顺序

1. 先在 `/settings/cloudmail` 完成配置
2. 再进入 `/chatgpt/accounts` 投递自动注册任务
3. 等任务结束后检查账号详情中的邮箱、密码、订阅信息和 2FA
