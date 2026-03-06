# OmniGate AlmaLinux Docker 部署说明

本文档对应当前仓库的五容器部署结构：

- `frontend`: Vue 生产静态资源 + Nginx 反向代理
- `backend`: Spring Boot 后端
- `worker`: Python 异步任务 Worker
- `postgres`: PostgreSQL 数据库
- `redis`: Redis Stream / 缓存

## 1. 在 AlmaLinux 安装 Docker

Docker 官方针对 RHEL 系列的安装方式同样适用于 AlmaLinux。官方文档使用 Docker 官方仓库，并通过 `docker-compose-plugin` 安装 Compose。

参考：

- [Docker Engine on RHEL](https://docs.docker.com/engine/install/rhel/)
- [Docker post-install](https://docs.docker.com/engine/install/linux-postinstall/)
- [Docker Compose plugin on Linux](https://docs.docker.com/compose/install/linux/)

执行：

```bash
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker run hello-world
```

如果你希望当前用户无需每次都加 `sudo`：

```bash
sudo usermod -aG docker $USER
newgrp docker
docker compose version
```

## 2. 准备部署文件

进入项目根目录：

```bash
cd /opt/OmniGate_website
cp .env.example .env
```

至少修改 `.env` 里的这几个值：

```env
POSTGRES_PASSWORD=一个强密码
OMNIGATE_JWT_SECRET=一个至少32位的随机密钥
FRONTEND_PORT=80
```

说明：

- 前端容器默认监听宿主机 `80`
- 后端、PostgreSQL、Redis 默认只暴露到 Docker 内部网络，不直接对公网开放
- `frontend` 会把 `/api` 和 `/ws/task-log` 反向代理到 `backend`

如果你想让宿主机 Nginx 接管 80 端口，再反代到前端容器，建议把 `.env` 改成：

```env
FRONTEND_BIND_HOST=127.0.0.1
FRONTEND_PORT=8088
HOST_NGINX_ENABLE=true
HOST_NGINX_SERVER_NAME=your-domain-or-server-ip
```

## 3. 构建并启动

首次部署：

```bash
docker compose build
docker compose up -d
```

如果你希望直接用仓库里的通用 Linux 脚本：

```bash
bash scripts/deploy-linux.sh
```

查看运行状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f frontend
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f postgres
docker compose logs -f redis
```

## 4. 容器职责与适配点

### frontend

- 基于 `omnigate_frontend/Dockerfile`
- 先用 Node 构建，再交给 Nginx 提供静态文件
- Nginx 已内置：
  - SPA 路由回退到 `index.html`
  - `/api` 代理到后端
  - `/ws/task-log` WebSocket 代理到后端

这意味着生产环境前端不需要把后端域名写死，默认同域访问即可。

### backend

- 基于 `omnigate_backend/Dockerfile`
- 使用 `SPRING_PROFILES_ACTIVE=prod`
- 通过环境变量连接 `postgres` 和 `redis`
- 启动时会执行 Flyway migration

### worker

- 基于 `omnigate_worker/Dockerfile`
- 容器内额外安装了 `chromium`
- 默认启用无头模式
- 默认关闭浏览器 sandbox，并配置了适合容器环境的 `BROWSER_ARGS`
- `docker-compose.yml` 已给 worker 设置 `shm_size`

如果你后续发现浏览器任务不稳定，优先调这两个值：

```env
WORKER_SHM_SIZE=1gb
BROWSER_ARGS=--disable-dev-shm-usage,--no-first-run,--disable-gpu,--disable-software-rasterizer
```

## 5. 常用运维命令

重启某个服务：

```bash
docker compose restart backend
docker compose restart worker
```

停止整套服务：

```bash
docker compose down
```

连同数据库和 Redis 数据一起删除：

```bash
docker compose down -v
```

拉起更新后的代码：

```bash
git pull
docker compose build
docker compose up -d
```

如果你希望直接由脚本自动 `git pull` 并完成更新：

```bash
bash scripts/update_deployed.sh
```

## 6. 脚本说明

### `scripts/deploy-linux.sh`

- 适用于首次部署
- 会检查 Docker / Docker Compose
- 如果本机未安装 Docker，会尝试使用官方安装脚本安装
- 如果 `.env` 不存在，会自动从 `.env.example` 生成
- 如果 `.env` 仍是默认数据库密码或默认 JWT 密钥，会中止部署
- 如果 `HOST_NGINX_ENABLE=true`，会自动安装并写入宿主机 Nginx 配置
- 宿主机 Nginx 默认反代到 `127.0.0.1:${FRONTEND_PORT}`

### `scripts/update_deployed.sh`

- 默认自动执行 `git fetch --all --prune` 和 `git pull --ff-only`
- 只重建 `frontend`、`backend`、`worker` 三个应用容器
- `postgres` 和 `redis` 数据卷不会被清空
- 如果存在未提交的本地改动，会先给出警告
- 如果启用了宿主机 Nginx，也会重新写入并重载 Nginx 配置

## 7. 对外访问

启动成功后：

- 前端访问：`http://服务器IP/`
- 前端会自动代理：
  - `http://服务器IP/api/...`
  - `ws://服务器IP/ws/task-log`

如果你要公网部署，建议再加一层 HTTPS 入口，例如：

- Caddy
- Nginx
- Traefik

当前这份 compose 先解决“单机 AlmaLinux 上把五个容器稳定跑起来”的问题，不包含 TLS 证书自动签发。
