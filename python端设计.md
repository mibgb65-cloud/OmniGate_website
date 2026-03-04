# 浏览器自动化 Worker 系统技术架构报告

## 1. 项目概览

本项目是一个 **浏览器自动化任务执行系统**，用于通过 Python Worker 执行无头浏览器脚本任务，并通过管理后台进行任务触发、监控和管理。

**系统主要特点：**

* 管理后台 **手动触发任务**
* Python Worker 执行 **浏览器自动化脚本**
* 单任务执行时间 **3–10 分钟**
* 默认并发 **3**，可配置 **1–10**
* 任务执行日志 **实时推送前端**
* 支持 **任务取消**
* 支持 **失败自动重试（最多3次）**
* 支持 **管理员动态配置系统参数**

**系统核心目标：**

* 将浏览器操作 **从主业务系统解耦**
* 提供 **可靠的任务执行与监控机制**
* 实现 **实时日志可视化**
* 保证 **任务执行可追溯与可管理**

---

## 2. 技术选型方案

### 2.1 技术栈

| 模块 | 技术 |
| --- | --- |
| **管理后台** | Spring Boot |
| **鉴权** | Spring Security + JWT 双 Token |
| **实时通信** | WebSocket |
| **Worker** | Python |
| **浏览器自动化** | nodriver（headless） |
| **任务队列** | Redis Stream |
| **日志流** | Redis Stream |
| **数据库** | PostgreSQL |
| **部署环境** | Linux Docker |

### 2.2 技术选型理由

* **Spring Boot：** 企业级稳定框架，与 Spring Security 集成良好，支持 WebSocket，生态成熟。适合作为 **管理后台与 API 服务**。
* **Python Worker：** Python 在自动化与浏览器控制领域生态成熟，`nodriver` 适用于反检测浏览器自动化，脚本任务开发效率高。适合作为 **任务执行节点**。
* **Redis Stream：** 支持 Consumer Group、消息确认 ACK、任务重放和高性能队列。相比 Redis List 更适合做 **任务系统**。
* **PostgreSQL：** 强一致性，支持 JSONB，查询能力强，适合存储任务记录与业务数据。作为 **任务状态唯一来源**。

---

## 3. 系统逻辑架构

### 3.1 系统架构图

```text
+---------------------+
|      Frontend       |
+----------+----------+
           |
           | REST API
           v
+---------------------+
|     Spring Boot     |
|   API + WebSocket   |
+----------+----------+
           |
     +-----+-----+
     |           |
     v           v
   Redis     PostgreSQL
     |
     v
+----------------------+
|    Python Worker     |
|   nodriver browser   |
+----------------------+

```

### 3.2 任务执行流程

**任务创建**

1. 管理员在前端触发任务
2. 前端调用 Spring Boot API
3. Spring Boot 创建 `task_runs` 记录
4. 任务写入 Redis Stream

**Worker 执行**

1. 从 Redis Stream 读取任务
2. 更新数据库状态为 `running`
3. 执行 nodriver 浏览器脚本
4. 将日志写入 Redis Stream
5. 写入 PostgreSQL 业务数据

**日志实时推送**

```text
  Worker
    |
    v
Redis Stream (log_stream)
    |
    v
Spring Boot
    |
    v
 WebSocket
    |
    v
 Frontend (实时展示日志)

```

---

## 4. 任务系统设计

### 4.1 任务状态机

```text
       queued
         |
         v
      running
      ├── success
      ├── failed
      ├── cancelled
      └── timeout

```

**状态含义：**
| 状态 | 说明 |
| :--- | :--- |
| `queued` | 等待执行 |
| `running` | 正在执行 |
| `success` | 执行成功 |
| `failed` | 执行失败 |
| `cancelled`| 管理员取消 |
| `timeout` | 执行超时 |

### 4.2 自动重试策略

任务失败后最多重试 **3 次**，每次延迟 **10 秒**（延迟时间管理员可配置）。

```text
       失败
         |
         v
attempt_no < max_attempts
         |
         v
等待 retry_delay_seconds
         |
         v
  创建新的 task_run

```

---

## 5. Redis Stream 设计

### 5.1 任务流

* **Stream 名称:** `task_stream`
* **Consumer Group:** `worker_group`

| 字段 | 含义 |
| --- | --- |
| `task_run_id` | 执行ID |
| `root_run_id` | 任务ID |
| `payload` | 参数 |
| `created_at` | 创建时间 |

### 5.2 日志流

* **Stream 名称:** `task_log_stream`

| 字段 | 含义 |
| --- | --- |
| `task_id` | 任务ID |
| `level` | INFO / ERROR |
| `message` | 日志内容 |
| `step` | 当前步骤 |
| `step_total` | 总步骤 |
| `timestamp` | 时间 |

> **示例：** `[3/12] 抓取商品列表`

---

# 6. 数据库设计

数据库采用 **PostgreSQL**，主要用于：

* 存储任务执行记录
* 保存任务状态
* 支持任务重试机制
* 提供任务历史审计能力

> **注意：** 日志数据不长期存储在数据库中，而是通过 **Redis Stream 实时传输**。

---

## 6.1 表：task_runs（任务执行记录表）

该表用于记录 **每一次任务执行尝试**。如果任务失败并自动重试，则会生成新的记录，并通过 `root_run_id` 关联同一任务链路。

```sql
CREATE TABLE task_runs (
  id UUID PRIMARY KEY,                        -- 当前执行记录ID（一次执行尝试）

  root_run_id UUID NOT NULL,                  -- 根任务ID，同一次任务的多次重试共享此ID

  attempt_no INT NOT NULL,                    -- 当前执行尝试次数（1,2,3）
  max_attempts INT DEFAULT 3,                 -- 最大允许重试次数（系统配置）

  status VARCHAR(32) NOT NULL,                -- 任务状态：queued/running/success/failed/cancelled/timeout

  triggered_by VARCHAR(128) NOT NULL,         -- 触发任务的管理员账号

  input_payload JSONB NOT NULL,               -- 任务输入参数（JSON格式）

  worker_instance_id VARCHAR(128),            -- 执行任务的Worker实例ID（容器名或hostname）

  started_at TIMESTAMPTZ,                     -- 任务开始执行时间
  finished_at TIMESTAMPTZ,                    -- 任务执行结束时间

  retry_of_run_id UUID,                       -- 如果是重试任务，则指向上一条执行记录ID

  next_retry_at TIMESTAMPTZ,                  -- 下一次重试时间（用于延迟重试调度）

  error_code VARCHAR(64),                     -- 错误代码（用于错误分类）
  error_message TEXT,                         -- 错误信息

  last_checkpoint VARCHAR(64),                -- 执行到的最后步骤（用于问题排查）

  cancel_requested_at TIMESTAMPTZ,            -- 管理员请求取消任务的时间
  cancelled_at TIMESTAMPTZ,                   -- Worker实际取消任务的时间

  heartbeat_at TIMESTAMPTZ,                   -- Worker心跳时间，用于检测任务是否卡死

  created_at TIMESTAMPTZ DEFAULT now(),       -- 记录创建时间
  updated_at TIMESTAMPTZ DEFAULT now()        -- 记录更新时间
);

```

---

## 6.2 索引设计

为了提高查询效率，需要建立以下索引：

```sql
CREATE INDEX idx_task_runs_root ON task_runs(root_run_id);
CREATE INDEX idx_task_runs_status ON task_runs(status);
CREATE INDEX idx_task_runs_created ON task_runs(created_at DESC);
CREATE INDEX idx_task_runs_worker ON task_runs(worker_instance_id);

```

**索引作用：**

| 索引 | 用途 |
| --- | --- |
| `idx_task_runs_root` | 查询同一任务的所有重试记录 |
| `idx_task_runs_status` | 查询待执行或运行中的任务 |
| `idx_task_runs_created` | 后台任务列表排序 |
| `idx_task_runs_worker` | 排查某个 Worker 执行的任务 |

---

## 6.3 系统配置表：system_settings

用于存储系统运行参数配置，管理员可通过后台修改。

```sql
CREATE TABLE system_settings (
  key VARCHAR PRIMARY KEY,                -- 配置键
  value VARCHAR,                          -- 配置值
  description VARCHAR,                    -- 配置说明
  updated_at TIMESTAMPTZ DEFAULT now()    -- 更新时间
);

```

**示例数据：**

| key | value | 说明 |
| --- | --- | --- |
| `worker.max_concurrency` | 3 | Worker默认并发数 |
| `worker.max_concurrency_limit` | 10 | Worker最大并发限制 |
| `task.retry_max_attempts` | 3 | 最大重试次数 |
| `task.retry_delay_seconds` | 10 | 任务重试延迟时间 |

> 管理员可以通过管理后台动态修改这些配置，Worker 定期刷新配置以生效。

---

## 6.4 任务重试机制（数据库层）

任务失败时：

1. 判断当前 `attempt_no`
2. 若小于 `max_attempts`，则等待延迟时间后
3. 创建新的 `task_run` 记录

**示例流程：** `root_run_id = A`

```text
attempt 1 -> failed
attempt 2 -> failed
attempt 3 -> success

```

**数据库记录：**

| id | root_run_id | attempt_no | status |
| --- | --- | --- | --- |
| `r1` | A | 1 | failed |
| `r2` | A | 2 | failed |
| `r3` | A | 3 | success |

这样可以完整记录**任务执行历史**。

---

## 6.5 任务卡死检测

* **Worker 更新：** Worker 每 **30 秒**更新数据库中的 `heartbeat_at`。
* **超时判定：** 如果满足 `now() - heartbeat_at > 2 minutes`，系统即可判定 Worker 可能异常。
* **后续处理：** 标记该任务为 `timeout` 或触发系统告警。

---

## 6.6 数据库职责边界

**数据库只负责：**

* 任务执行记录
* 状态存储
* 错误信息
* 审计追踪

**日志数据流向：**
`Worker` -> `Redis Stream` -> `WebSocket` -> `Frontend`
*(日志数据不会长期存储在 PostgreSQL 中，保持数据库轻量)*

---

## 7. WebSocket 设计

* **连接方式:** `ws://host/ws/task-log`
* **认证:** `Authorization: Bearer access_token`

**消息示例：**

```json
{
  "task_id": "uuid",
  "level": "INFO",
  "step": 3,
  "step_total": 12,
  "message": "抓取商品列表"
}

```

---

## 8. Worker 并发控制

* **控制方式:** Worker 内使用并发控制 `asyncio.Semaphore(max_concurrency)`
* **并发来源:** 从数据库 `system_settings` 表读取
* **范围:** 1 ≤ concurrency ≤ 10 （默认：3）

---

## 9. Docker 部署方案

推荐使用 **Docker Compose** 进行编排。

**核心服务:**

* `springboot-api`
* `python-worker`
* `redis`
* `postgres`

**示例目录结构：**

```text
project/
 ├── docker-compose.yml
 ├── backend/
 ├── worker/
 └── frontend/

```

---

## 10. 监控与运维

* **Worker 心跳:** Worker 每 30 秒更新一次数据库中的 `heartbeat_at`。
* **卡死检测规则:** 如果 `now() - heartbeat_at > 2min`，则判定任务/Worker已卡死。
* **Redis 日志裁剪:** 日志流需设置 `MAXLEN ~ 10000`，避免占用过多内存导致日志无限增长。

---

## 11. 系统扩展能力

当前系统设计为**单机 Worker**，但为未来扩展留足了空间：

* **增加 Worker 实例:** 由于使用了 Redis Stream Consumer Group，天生支持多 Worker 负载均衡消费。
* **扩展性:** 无需修改现有系统架构即可实现水平扩容。

---

## 12. 总结

该架构实现了：

1. 浏览器自动化任务的**解耦执行**
2. **实时日志监控**
3. **可取消任务**与**自动重试机制**
4. 管理员**动态配置**
5. 任务执行的**全面可追溯**

系统具备**良好的稳定性**、**清晰的架构边界**以及**可扩展的分布式能力**，非常适用于构建浏览器自动化任务执行平台。

```Plaintext
omnigate_worker/
├── src/
│   ├── main.py                     # Worker 启动入口
│   ├── config.py                   # 全局配置
│   │
│   ├── core/                       # 核心基础设施 (全局共享)
│   │   ├── worker_node.py          # 核心并发调度与任务路由分发
│   │   ├── heartbeat.py            
│   │   └── state_manager.py        
│   │
│   ├── db/                         # 数据库交互 (全局共享)
│   ├── redis_io/                   # Redis 通信 (全局共享)
│   ├── utils/                      # 通用工具类 (日志、异常等)
│   │
│   ├── browser/                    # 浏览器底层控制 (全局共享)
│   │   ├── __init__.py
│   │   ├── browser_manager.py      # nodriver 实例池、代理配置、指纹伪装
│   │   └── interceptor.py          # 全局请求拦截器 (如果需要拦截特定请求)
│   │
│   └── modules/                    # ★ 业务模块层 (按目标平台严格隔离) ★
│       ├── __init__.py
│       ├── base_task.py            # 所有业务任务的抽象基类 (定义统一的 run() 接口)
│       │
│       ├── github/                 # GitHub 自动化模块
│       │   ├── __init__.py
│       │   ├── auth.py             # GitHub 专属：处理登录、2FA、Cookie 保持
│       │   ├── helpers.py          # GitHub 专属：解析仓库DOM、处理特定弹窗
│       │   └── tasks/              # GitHub 具体的任务入口
│       │       ├── clone_repo.py
│       │       └── star_project.py
│       │
│       ├── google/                 # Google 自动化模块
│       │   ├── __init__.py
│       │   ├── auth.py             # Google 专属：绕过人机验证、多账号切换
│       │   ├── helpers.py          # Google 专属：解析搜索结果页
│       │   └── tasks/
│       │       ├── search_keyword.py
│       │       └── scrape_maps.py
│       │
│       └── chatgpt/                # ChatGPT 自动化模块
│           ├── __init__.py
│           ├── auth.py             # ChatGPT 专属：Cloudflare 绕过、Token 刷新
│           ├── helpers.py          # ChatGPT 专属：等待流式响应输出完成、提取 Markdown
│           └── tasks/
│               ├── generate_text.py
│               └── create_session.py
│
├── requirements.txt
└── Dockerfile
```

