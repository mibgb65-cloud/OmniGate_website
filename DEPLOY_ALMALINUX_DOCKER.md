# OmniGate AlmaLinux Docker 部署说明

本文档对应当前仓库的五容器单机部署结构：

- `frontend`: Vue 生产静态资源 + Nginx 代理
- `backend`: Spring Boot 后端
- `worker`: Python 异步任务 Worker
- `postgres`: PostgreSQL
- `redis`: Redis

更细的故障定位见 [OPERATIONS_TROUBLESHOOTING.md](./OPERATIONS_TROUBLESHOOTING.md)。

## 1. 推荐部署方式

优先使用仓库自带脚本：

- 首次部署：`bash scripts/deploy-linux.sh`
- 更新部署：`bash scripts/update_deployed.sh`

这两份脚本已经覆盖了：

- Docker / Compose 可用性检查
- `.env` 自动生成与基础校验
- Docker Compose 配置校验
- 应用镜像构建与容器启动
- 可选的宿主机 Nginx 反向代理配置
- 部署完成后的访问提示

## 2. AlmaLinux 8/9 环境准备

先安装基础工具：

```bash
sudo dnf -y update
sudo dnf -y install git curl ca-certificates dnf-plugins-core
sudo systemctl enable --now firewalld
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

再安装 Docker 官方仓库和 Compose 插件：

```bash
sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker run hello-world
```

如果你希望当前用户后续可以直接执行 `docker`：

```bash
sudo usermod -aG docker $USER
newgrp docker
docker compose version
```

说明：

- 如果你跳过手动安装，`scripts/deploy-linux.sh` 在未检测到 Docker 时也会尝试自动安装
- 生产环境仍建议你先手动装好 Docker，这样日志和包源更可控

## 3. 获取代码

建议把仓库放在固定目录，例如 `/opt/OmniGate_website`：

```bash
sudo mkdir -p /opt/OmniGate_website
sudo chown "$USER":"$USER" /opt/OmniGate_website
cd /opt/OmniGate_website
git clone <你的仓库地址> .
```

注意：

- 请在空目录里执行 `git clone ... .`
- 不要先 `cd OmniGate_website` 再 clone 一次同名目录，否则会出现“目录套目录”，后面找不到 `.env.example`

## 4. 准备 `.env`

复制示例文件：

```bash
cd /opt/OmniGate_website
cp .env.example .env
```

至少修改这些值：

```env
POSTGRES_PASSWORD=一个强密码
OMNIGATE_JWT_SECRET=一个至少32位的随机密钥
FRONTEND_API_BASE_URL=/
FRONTEND_PORT=80
```

说明：

- `FRONTEND_API_BASE_URL` 推荐设为 `/`
- 当前前端版本也兼容 `/api`，但 `/` 更适合作为默认值，能减少旧前端构建产物出现 `/api/api/...` 路径的风险
- `POSTGRES_PASSWORD` 可以包含 `@`、`#` 等特殊字符，当前 worker 已兼容

### 4.1 直接由前端容器对外提供服务

这是最简单的单机方案：

```env
FRONTEND_BIND_HOST=0.0.0.0
FRONTEND_PORT=80
HOST_NGINX_ENABLE=false
```

访问地址通常就是：

```text
http://服务器IP/
```

### 4.2 宿主机 Nginx 接管 80 端口

如果你要让宿主机 Nginx 再反代到前端容器，改成：

```env
FRONTEND_BIND_HOST=127.0.0.1
FRONTEND_PORT=8088
HOST_NGINX_ENABLE=true
HOST_NGINX_SERVER_NAME=你的域名或服务器IP
```

说明：

- 这时前端容器不会直接暴露到公网
- 脚本会自动写宿主机 Nginx 配置，并把流量转发到 `127.0.0.1:${FRONTEND_PORT}`
- 如果 AlmaLinux 开启了 SELinux `Enforcing`，脚本还会自动执行 `setsebool -P httpd_can_network_connect 1`

## 5. 首次部署

执行：

```bash
cd /opt/OmniGate_website
bash scripts/deploy-linux.sh
```

脚本会：

- 检查 Linux / Docker / Compose
- 检查并加载 `.env`
- 校验默认密码、JWT 密钥长度、端口和并发配置
- 校验 Docker Compose
- 构建镜像并启动容器
- 在启用 `HOST_NGINX_ENABLE=true` 时配置宿主机 Nginx

部署后建议立刻检查：

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f worker
```

## 6. 更新已部署环境

如果服务器代码目录本身就是 Git 仓库，更新直接用：

```bash
cd /opt/OmniGate_website
bash scripts/update_deployed.sh
```

这份脚本会：

- `git fetch --all --prune`
- `git pull --ff-only`
- 重建 `frontend`、`backend`、`worker`
- 保留 `postgres` 和 `redis` 数据卷

不要轻易执行：

```bash
docker compose down -v
```

这会删除数据库和 Redis 数据卷。

## 7. 常用运维命令

查看状态：

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

只重启某个服务：

```bash
docker compose restart backend
docker compose restart worker
```

重新构建某个服务：

```bash
docker compose build frontend
docker compose up -d frontend
```

进入数据库：

```bash
docker compose exec postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

## 8. 默认访问与登录

如果数据库是首次初始化，默认管理员来自 Flyway 初始化脚本：

```text
username: admin
password: ChangeMe123!
```

首次登录后请立即修改密码。

## 9. 常见排查入口

如果你不知道问题在哪，优先按这个顺序排：

1. `docker compose ps`
2. `docker compose logs -f backend`
3. `docker compose logs -f worker`
4. `docker compose logs -f frontend`
5. 云厂商安全组 / `firewalld` / 域名解析

典型问题和处理方式请看：

- [OPERATIONS_TROUBLESHOOTING.md](./OPERATIONS_TROUBLESHOOTING.md)

其中已经整理了这些常见场景：

- 页面打不开或 502 / 504
- 登录请求变成 `/api/api/auth/login`
- Worker 启动时数据库主机解析失败
- Worker 任务反复重试但前端只看到“队列中/执行中”
- 宿主机 Nginx 在 AlmaLinux + SELinux 下无法反代

## 10. 相关文档

- [README.md](./README.md)
- [OPERATIONS_TROUBLESHOOTING.md](./OPERATIONS_TROUBLESHOOTING.md)
- [docker-compose.yml](./docker-compose.yml)
- [scripts/deploy-linux.sh](./scripts/deploy-linux.sh)
- [scripts/update_deployed.sh](./scripts/update_deployed.sh)
