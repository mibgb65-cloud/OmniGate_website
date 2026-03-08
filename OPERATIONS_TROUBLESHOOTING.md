# OmniGate 运维排障手册

本文档聚焦单机 Docker 部署后的常见问题定位，默认对应当前仓库版本。

## 1. 先做这四步

无论具体问题是什么，先执行：

```bash
docker compose ps
docker compose logs --tail=120 backend
docker compose logs --tail=120 worker
docker compose logs --tail=120 frontend
```

优先判断：

- 是容器没起来
- 是容器起来了但不健康
- 还是容器健康、但入口代理或前端请求路径不对

## 2. 页面打不开

常见表现：

- 浏览器直接超时
- 域名打不开
- 打开后是 502 / 504

排查顺序：

1. 检查容器状态

```bash
docker compose ps
```

2. 检查端口监听

```bash
ss -lntp | grep -E ':80|:8088'
```

3. 检查防火墙

```bash
sudo firewall-cmd --list-services
sudo firewall-cmd --list-ports
```

4. 检查云厂商安全组是否放通 `80/443`

处理建议：

- 如果 `frontend` 没起来，先看 `docker compose logs -f frontend`
- 如果 `HOST_NGINX_ENABLE=true`，再看宿主机 Nginx：

```bash
sudo nginx -t
sudo systemctl status nginx
```

## 3. 登录接口请求成 `/api/api/auth/login`

常见表现：

- 前端网络请求地址是 `/api/api/auth/login`
- 登录直接报 `401` 或请求路径明显重复

原因：

- 旧前端构建产物把 `VITE_API_BASE_URL` 设成了 `/api`
- 前端接口文件本身又已经写了 `/api/...`

当前仓库版本已经兼容 `/` 和 `/api`，但推荐配置仍然是：

```env
FRONTEND_API_BASE_URL=/
```

处理步骤：

```bash
grep '^FRONTEND_API_BASE_URL=' .env
docker compose build frontend
docker compose up -d frontend
```

如果前面挂了 CDN 或 Cloudflare，再清一次缓存。

## 4. 登录 401，但日志里显示“账号或密码错误”

先看 `backend` 日志是否有这类信息：

```text
登录认证失败，message=用户名或密码错误
```

这通常就是密码错，不是部署问题。

如果是首次初始化数据库，默认管理员是：

```text
username: admin
password: ChangeMe123!
```

如果你之前已经部署过并保留了旧卷，数据库不会因为更新镜像自动重置。

## 5. Worker 启动时报 `socket.gaierror: [Errno -2] Name or service not known`

常见表现：

- `docker compose logs -f worker` 里出现：

```text
socket.gaierror: [Errno -2] Name or service not known
```

优先检查：

1. 你是不是还在运行旧镜像
2. 当前代码是否已经包含分字段 PostgreSQL 配置
3. `.env` 里的数据库密码是否和服务端一致

当前仓库版本的 `worker` 已改成：

- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

所以处理通常是重新拉代码并重建 worker：

```bash
git pull --ff-only
docker compose build worker
docker compose up -d worker
```

## 6. Worker 一直重试，前端只看到任务卡着

常见表现：

- `worker` 日志反复出现 `Retry task requeued`
- 前端状态长时间停在执行中或等待中

排查方式：

```bash
docker compose logs -f worker
docker compose logs -f backend
```

要点：

- `worker` 负责真正执行浏览器任务和写回 Redis / PostgreSQL
- `backend` 负责状态查询、批量状态接口、WebSocket 日志转发

如果 `worker` 有异常而 `backend` 没异常，优先修 worker。

如果 `backend` 在状态查询接口报错，前端也可能一直拿不到正确任务状态。

## 7. Google 任务状态批量查询报 MyBatis UUID type handler 错误

常见表现：

`backend` 日志类似：

```text
Type handler was null on parameter mapping for property '__frch_rootRunId_0'
```

这说明服务器还在跑旧版后端镜像。处理方式：

```bash
git pull --ff-only
docker compose build backend
docker compose up -d backend
```

如果你是整仓更新，也可以直接：

```bash
bash scripts/update_deployed.sh
```

## 8. 宿主机 Nginx 已启用，但 AlmaLinux 上反代失败

常见表现：

- `curl http://127.0.0.1:8088` 正常
- 访问域名却 502
- Nginx 日志里能看到 upstream connect failed

在 AlmaLinux / RHEL 系里，如果 SELinux 是 `Enforcing`，通常要允许 Nginx 发起网络连接：

```bash
sudo setsebool -P httpd_can_network_connect 1
```

当前部署脚本在 `HOST_NGINX_ENABLE=true` 时会自动尝试配置这项，但手工排障时仍建议确认：

```bash
getenforce
```

## 9. WebSocket 日志不工作，但页面其余接口正常

先确认：

```bash
grep '^FRONTEND_TASK_LOG_WS_URL=' .env
```

推荐：

- 留空，使用默认同源 `/ws/task-log`
- 或显式设为 `/ws/task-log`

如果你在宿主机 Nginx 或外部 CDN 上又套了一层代理，确认它支持：

- `Upgrade`
- `Connection`
- 长连接超时

仓库内置的前端容器 Nginx 和脚本生成的宿主机 Nginx 配置都已经包含 WebSocket 代理头。

## 10. 更新脚本执行失败

常见原因：

- 当前目录不是 Git 仓库
- 本地有未提交改动，`git pull --ff-only` 失败
- 服务器代码目录是“目录套目录”

先看：

```bash
pwd
git status --short
ls -la
```

如果你误操作成：

```text
/opt/OmniGate_website/OmniGate_website
```

那就进入真正的仓库层级再执行脚本。

## 11. 有用的临时命令

查看 Compose 渲染后的最终配置：

```bash
docker compose config
```

查看某个容器最近 200 行日志：

```bash
docker compose logs --tail=200 backend
docker compose logs --tail=200 worker
```

检查 PostgreSQL 是否健康：

```bash
docker compose exec postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

检查 Redis 是否正常：

```bash
docker compose exec redis redis-cli ping
```

## 12. 如果还是没定位出来

把下面四段输出一起贴出来，通常就足够定位：

```bash
docker compose ps
docker compose logs --tail=120 frontend
docker compose logs --tail=120 backend
docker compose logs --tail=120 worker
```
