from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import asyncpg


def utc_now() -> datetime:
    """统一生成带 UTC 时区的当前时间。"""

    return datetime.now(timezone.utc)


@dataclass(slots=True)
class TaskRunRecord:
    """`task_runs` 表里当前执行记录的核心字段。"""

    id: UUID
    root_run_id: UUID
    attempt_no: int
    max_attempts: int
    triggered_by: str
    input_payload: dict
    status: str


class TaskRunRepository:
    """封装 worker 任务生命周期相关的数据库读写。"""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_task_run(self, task_run_id: UUID) -> TaskRunRecord | None:
        """读取一条任务运行记录，供重试和状态推进逻辑使用。"""

        query = """
            SELECT id, root_run_id, attempt_no, max_attempts, triggered_by, input_payload, status
            FROM task_runs
            WHERE id = $1
        """
        row = await self._pool.fetchrow(query, task_run_id)
        if row is None:
            return None
        return TaskRunRecord(
            id=row["id"],
            root_run_id=row["root_run_id"],
            attempt_no=row["attempt_no"],
            max_attempts=row["max_attempts"],
            triggered_by=row["triggered_by"],
            input_payload=self._decode_payload(row["input_payload"]),
            status=row["status"],
        )

    async def mark_running(self, task_run_id: UUID, worker_instance_id: str) -> bool:
        """
        把 queued 状态推进到 running。

        返回值表示这次更新是否真正生效，可用来避免多个 worker 重复抢到同一任务。
        """

        query = """
            UPDATE task_runs
            SET status = 'running',
                worker_instance_id = $2,
                started_at = COALESCE(started_at, now()),
                heartbeat_at = now(),
                updated_at = now()
            WHERE id = $1
              AND status = 'queued'
        """
        result = await self._pool.execute(query, task_run_id, worker_instance_id)
        return self._updated(result)

    async def mark_success(self, task_run_id: UUID, last_checkpoint: str | None = None) -> None:
        """任务执行成功后写回最终状态，并清空错误信息。"""

        query = """
            UPDATE task_runs
            SET status = 'success',
                last_checkpoint = $2,
                error_code = NULL,
                error_message = NULL,
                heartbeat_at = now(),
                finished_at = now(),
                updated_at = now()
            WHERE id = $1
        """
        await self._pool.execute(query, task_run_id, last_checkpoint)

    async def mark_cancelled(self, task_run_id: UUID, reason: str | None = None) -> None:
        """把任务标记为已取消，并记录取消原因。"""

        query = """
            UPDATE task_runs
            SET status = 'cancelled',
                error_message = COALESCE($2, error_message),
                cancelled_at = now(),
                finished_at = now(),
                heartbeat_at = now(),
                updated_at = now()
            WHERE id = $1
        """
        await self._pool.execute(query, task_run_id, reason)

    async def mark_timeout(self, task_run_id: UUID, reason: str | None = None) -> None:
        """把任务标记为超时，默认补一个 TIMEOUT 错误码。"""

        query = """
            UPDATE task_runs
            SET status = 'timeout',
                error_code = COALESCE(error_code, 'TIMEOUT'),
                error_message = COALESCE($2, error_message),
                finished_at = now(),
                heartbeat_at = now(),
                updated_at = now()
            WHERE id = $1
        """
        await self._pool.execute(query, task_run_id, reason)

    async def mark_failed_and_schedule_retry(
        self,
        *,
        task_run_id: UUID,
        error_code: str | None,
        error_message: str | None,
        last_checkpoint: str | None,
        retry_delay_seconds: int,
        retry_max_attempts: int | None = None,
    ) -> UUID | None:
        """
        当前执行失败后，必要时直接生成下一次重试记录。

        返回新任务 run_id；如果不再允许重试，则返回 None。
        """

        current = await self.get_task_run(task_run_id)
        if current is None:
            return None

        effective_max_attempts = max(1, retry_max_attempts or current.max_attempts)
        next_run_id: UUID | None = None
        next_retry_at: datetime | None = None
        if current.attempt_no < effective_max_attempts:
            next_run_id = uuid4()
            next_retry_at = utc_now() + timedelta(seconds=max(0, retry_delay_seconds))

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # 先把本次执行落为 failed，再视情况补一条新的 queued 记录。
                await conn.execute(
                    """
                    UPDATE task_runs
                    SET status = 'failed',
                        error_code = $2,
                        error_message = $3,
                        last_checkpoint = $4,
                        heartbeat_at = now(),
                        finished_at = now(),
                        updated_at = now()
                    WHERE id = $1
                    """,
                    task_run_id,
                    error_code,
                    error_message,
                    last_checkpoint,
                )

                if next_run_id is not None and next_retry_at is not None:
                    await conn.execute(
                        """
                        INSERT INTO task_runs (
                            id,
                            root_run_id,
                            attempt_no,
                            max_attempts,
                            status,
                            triggered_by,
                            input_payload,
                            retry_of_run_id,
                            next_retry_at,
                            created_at,
                            updated_at
                        )
                        VALUES (
                            $1,
                            $2,
                            $3,
                            $4,
                            'queued',
                            $5,
                            $6::jsonb,
                            $7,
                            $8,
                            now(),
                            now()
                        )
                        """,
                        next_run_id,
                        current.root_run_id,
                        current.attempt_no + 1,
                        effective_max_attempts,
                        current.triggered_by,
                        json.dumps(current.input_payload, ensure_ascii=False),
                        current.id,
                        next_retry_at,
                    )
        return next_run_id

    async def update_heartbeat(self, task_run_id: UUID) -> None:
        """运行中的任务定期刷新心跳，便于外部判断是否卡死。"""

        query = """
            UPDATE task_runs
            SET heartbeat_at = now(),
                updated_at = now()
            WHERE id = $1
              AND status = 'running'
        """
        await self._pool.execute(query, task_run_id)

    async def is_cancel_requested(self, task_run_id: UUID) -> bool:
        """查询任务是否已经被外部请求取消。"""

        query = """
            SELECT cancel_requested_at IS NOT NULL
            FROM task_runs
            WHERE id = $1
        """
        result = await self._pool.fetchval(query, task_run_id)
        return bool(result)

    async def set_google_account_sync_status(self, account_id: int, sync_status: int) -> None:
        """同步更新 Google 账号表上的同步状态，给后台页面展示使用。"""

        query = """
            UPDATE acc_google_base
            SET sync_status = $2,
                updated_at = now()
            WHERE id = $1
              AND deleted = 0
        """
        await self._pool.execute(query, account_id, sync_status)

    @staticmethod
    def _updated(result: str) -> bool:
        # asyncpg 返回的是类似 'UPDATE 1' 这样的命令字符串，这里只关心影响行数是否大于 0。
        return result.split()[-1] != "0"

    @staticmethod
    def _decode_payload(payload: object) -> dict:
        """把 JSONB / 字符串 payload 安全转成 dict，异常时降级为空对象。"""

        if isinstance(payload, dict):
            return payload
        if isinstance(payload, str):
            try:
                parsed = json.loads(payload)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}
