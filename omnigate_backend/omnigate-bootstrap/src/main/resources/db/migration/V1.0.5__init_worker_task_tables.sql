-- Worker 任务系统初始化表结构

-- 任务执行记录表：记录每次执行尝试（含重试）
CREATE TABLE IF NOT EXISTS task_runs
(
    id                  UUID PRIMARY KEY,
    root_run_id         UUID         NOT NULL,
    attempt_no          INT          NOT NULL,
    max_attempts        INT          NOT NULL DEFAULT 3,
    status              VARCHAR(32)  NOT NULL,
    triggered_by        VARCHAR(128) NOT NULL,
    input_payload       JSONB        NOT NULL,
    worker_instance_id  VARCHAR(128),
    started_at          TIMESTAMPTZ,
    finished_at         TIMESTAMPTZ,
    retry_of_run_id     UUID,
    next_retry_at       TIMESTAMPTZ,
    error_code          VARCHAR(64),
    error_message       TEXT,
    last_checkpoint     VARCHAR(64),
    cancel_requested_at TIMESTAMPTZ,
    cancelled_at        TIMESTAMPTZ,
    heartbeat_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);

COMMENT ON TABLE task_runs IS 'Worker任务执行记录表';
COMMENT ON COLUMN task_runs.id IS '当前执行记录ID（一次执行尝试）';
COMMENT ON COLUMN task_runs.root_run_id IS '根任务ID，同一次任务多次重试共享';
COMMENT ON COLUMN task_runs.attempt_no IS '当前执行次数（1,2,3...）';
COMMENT ON COLUMN task_runs.max_attempts IS '最大允许重试次数';
COMMENT ON COLUMN task_runs.status IS '任务状态：queued/running/success/failed/cancelled/timeout';
COMMENT ON COLUMN task_runs.triggered_by IS '触发任务的管理员账号';
COMMENT ON COLUMN task_runs.input_payload IS '任务输入参数';
COMMENT ON COLUMN task_runs.worker_instance_id IS '执行任务的Worker实例ID';
COMMENT ON COLUMN task_runs.started_at IS '开始执行时间';
COMMENT ON COLUMN task_runs.finished_at IS '结束执行时间';
COMMENT ON COLUMN task_runs.retry_of_run_id IS '若为重试任务，指向上一条执行记录';
COMMENT ON COLUMN task_runs.next_retry_at IS '下一次重试时间';
COMMENT ON COLUMN task_runs.error_code IS '错误代码';
COMMENT ON COLUMN task_runs.error_message IS '错误信息';
COMMENT ON COLUMN task_runs.last_checkpoint IS '最后执行检查点';
COMMENT ON COLUMN task_runs.cancel_requested_at IS '取消请求时间';
COMMENT ON COLUMN task_runs.cancelled_at IS '实际取消时间';
COMMENT ON COLUMN task_runs.heartbeat_at IS '任务心跳时间';
COMMENT ON COLUMN task_runs.created_at IS '创建时间';
COMMENT ON COLUMN task_runs.updated_at IS '更新时间';

CREATE INDEX IF NOT EXISTS idx_task_runs_root ON task_runs (root_run_id);
CREATE INDEX IF NOT EXISTS idx_task_runs_status ON task_runs (status);
CREATE INDEX IF NOT EXISTS idx_task_runs_created ON task_runs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_task_runs_worker ON task_runs (worker_instance_id);

DO
$$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_task_runs_retry_of_run_id') THEN
        ALTER TABLE task_runs
            ADD CONSTRAINT fk_task_runs_retry_of_run_id
                FOREIGN KEY (retry_of_run_id) REFERENCES task_runs (id);
    END IF;
END
$$;

-- 系统运行参数表：管理员可动态调整Worker并发和重试策略
CREATE TABLE IF NOT EXISTS system_settings
(
    key         VARCHAR(128) PRIMARY KEY,
    value       VARCHAR(1024),
    description VARCHAR(255),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE system_settings IS '系统配置表';
COMMENT ON COLUMN system_settings.key IS '配置键';
COMMENT ON COLUMN system_settings.value IS '配置值';
COMMENT ON COLUMN system_settings.description IS '配置说明';
COMMENT ON COLUMN system_settings.updated_at IS '更新时间';

INSERT INTO system_settings (key, value, description)
VALUES ('worker.max_concurrency', '3', 'Worker默认并发数')
ON CONFLICT (key) DO NOTHING;

INSERT INTO system_settings (key, value, description)
VALUES ('worker.max_concurrency_limit', '10', 'Worker最大并发限制')
ON CONFLICT (key) DO NOTHING;

INSERT INTO system_settings (key, value, description)
VALUES ('task.retry_max_attempts', '3', '任务最大重试次数')
ON CONFLICT (key) DO NOTHING;

INSERT INTO system_settings (key, value, description)
VALUES ('task.retry_delay_seconds', '10', '任务失败后重试延迟秒数')
ON CONFLICT (key) DO NOTHING;
