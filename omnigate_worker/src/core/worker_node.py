from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg

from src.config import Settings
from src.core.heartbeat import HeartbeatService
from src.core.state_manager import TaskStateManager, WorkerRuntimeSettings
from src.modules.chatgpt.actions import create_task
from src.redis_io import RedisStreamClient, TaskStreamMessage


logger = logging.getLogger(__name__)
LOG_PREFIX = "[Worker节点]"


class WorkerNode:
    FEATURE_SYNC_ACTION = "get_google_account_feature_by_account_id"
    ACCOUNT_SYNC_STATUS_WAITING = 1
    ACCOUNT_SYNC_STATUS_RUNNING = 2
    ACCOUNT_SYNC_STATUS_SUCCESS = 3
    ACCOUNT_SYNC_STATUS_FAILED = 4

    def __init__(
        self,
        *,
        settings: Settings,
        db_pool: asyncpg.Pool,
        state_manager: TaskStateManager,
        stream_client: RedisStreamClient,
        heartbeat_service: HeartbeatService,
    ) -> None:
        self._settings = settings
        self._db_pool = db_pool
        self._state_manager = state_manager
        self._stream_client = stream_client
        self._heartbeat_service = heartbeat_service
        self._stop_event = asyncio.Event()
        self._active_tasks: set[asyncio.Task[None]] = set()
        self._retry_enqueue_tasks: set[asyncio.Task[None]] = set()
        self._semaphore: asyncio.Semaphore | None = None
        self._runtime: WorkerRuntimeSettings | None = None
        self._pending_claim_cursor: str = "0-0"
        self._next_pending_claim_at: float = 0.0

    async def start(self) -> None:
        await self._stream_client.connect()
        await self._stream_client.ensure_group(
            stream=self._settings.task_stream,
            group=self._settings.task_stream_group,
        )
        self._runtime = await self._state_manager.get_runtime_settings()
        self._semaphore = asyncio.Semaphore(self._runtime.max_concurrency)

        logger.info(
            (
                "%s Worker 已启动 | stream=%s | group=%s | consumer=%s | concurrency=%s "
                "| claim_idle_ms=%s | claim_count=%s | claim_interval_ms=%s"
            ),
            LOG_PREFIX,
            self._settings.task_stream,
            self._settings.task_stream_group,
            self._consumer_name,
            self._runtime.max_concurrency,
            self._settings.task_stream_claim_idle_ms,
            self._settings.task_stream_claim_count,
            self._settings.task_stream_claim_interval_ms,
        )

        try:
            await self._consume_loop()
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        self._stop_event.set()
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)
        if self._retry_enqueue_tasks:
            for task in self._retry_enqueue_tasks:
                task.cancel()
            await asyncio.gather(*self._retry_enqueue_tasks, return_exceptions=True)
        await self._heartbeat_service.shutdown()
        await self._stream_client.close()

    async def _consume_loop(self) -> None:
        assert self._runtime is not None
        assert self._semaphore is not None

        while not self._stop_event.is_set():
            available = self._runtime.max_concurrency - len(self._active_tasks)
            if available <= 0:
                await asyncio.sleep(0.05)
                continue

            read_count = min(max(1, self._settings.task_stream_read_count), available)
            messages = await self._stream_client.read_group(
                stream=self._settings.task_stream,
                group=self._settings.task_stream_group,
                consumer=self._consumer_name,
                count=read_count,
                block_ms=self._settings.task_stream_block_ms,
            )
            if not messages:
                messages = await self._read_pending_messages(available=available)
                if not messages:
                    continue

            for message in messages:
                await self._semaphore.acquire()
                worker = asyncio.create_task(self._process_message(message))
                self._active_tasks.add(worker)
                worker.add_done_callback(self._on_worker_done)

    async def _read_pending_messages(self, *, available: int) -> list[TaskStreamMessage]:
        loop = asyncio.get_running_loop()
        now = loop.time()
        if now < self._next_pending_claim_at:
            return []

        claim_count = min(max(1, self._settings.task_stream_claim_count), available)
        try:
            next_cursor, claimed_messages = await self._stream_client.auto_claim(
                stream=self._settings.task_stream,
                group=self._settings.task_stream_group,
                consumer=self._consumer_name,
                min_idle_ms=self._settings.task_stream_claim_idle_ms,
                start_id=self._pending_claim_cursor,
                count=claim_count,
            )
            self._pending_claim_cursor = next_cursor
        except Exception:  # noqa: BLE001
            logger.exception("%s 自动认领 pending 消息失败", LOG_PREFIX)
            self._next_pending_claim_at = now + max(0.5, self._settings.task_stream_claim_interval_ms / 1000.0)
            return []

        if not claimed_messages:
            self._next_pending_claim_at = now + max(0.5, self._settings.task_stream_claim_interval_ms / 1000.0)
            return []

        self._next_pending_claim_at = now
        logger.info(
            "%s 已自动认领 pending 消息 | consumer=%s | count=%s | next_cursor=%s",
            LOG_PREFIX,
            self._consumer_name,
            len(claimed_messages),
            self._pending_claim_cursor,
        )
        return claimed_messages

    def _on_worker_done(self, task: asyncio.Task[None]) -> None:
        self._active_tasks.discard(task)
        if self._semaphore is not None:
            self._semaphore.release()
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            return
        if exc:
            logger.exception("%s 单个 task worker 异常退出", LOG_PREFIX)

    async def _process_message(self, message: TaskStreamMessage) -> None:
        task_run_id = self._parse_task_run_id(message.fields.get("task_run_id"))
        if task_run_id is None:
            logger.error("%s 跳过无效 task_run_id 的消息 | message_id=%s", LOG_PREFIX, message.message_id)
            await self._ack_message(message)
            return

        try:
            await self._handle_task(task_run_id=task_run_id, message=message)
        finally:
            await self._ack_message(message)

    async def _handle_task(self, *, task_run_id: UUID, message: TaskStreamMessage) -> None:
        if not await self._state_manager.mark_running(task_run_id, self._settings.worker_instance_id):
            logger.info("%s 任务状态不是 queued，跳过执行 | task_run_id=%s", LOG_PREFIX, task_run_id)
            return

        task_record = await self._state_manager.get_task_run(task_run_id)
        if task_record is None:
            logger.error("%s 未找到 task_runs 记录 | task_run_id=%s", LOG_PREFIX, task_run_id)
            return

        task_payload = self._extract_task_payload(message.fields)
        if not task_payload:
            await self._state_manager.mark_failed_and_schedule_retry(
                task_run_id=task_run_id,
                error_code="INVALID_PAYLOAD",
                error_message="Missing or invalid payload in task stream message",
                last_checkpoint="decode_payload",
                retry_delay_seconds=0,
                retry_max_attempts=task_record.attempt_no,
            )
            return

        if await self._state_manager.is_cancel_requested(task_run_id):
            await self._state_manager.mark_cancelled(task_run_id, reason="Cancelled before execution")
            await self._sync_feature_status_if_needed(task_payload, self.ACCOUNT_SYNC_STATUS_FAILED)
            return

        await self._sync_feature_status_if_needed(task_payload, self.ACCOUNT_SYNC_STATUS_RUNNING)
        await self._heartbeat_service.start(task_run_id)
        try:
            task = create_task(
                task_payload=task_payload,
                task_id=str(task_run_id),
                worker_instance_id=self._settings.worker_instance_id,
                attempt_no=task_record.attempt_no,
                log_sink=self._build_task_log_sink(task_run_id=task_run_id, root_run_id=task_record.root_run_id),
                db_pool=self._db_pool,
            )
            biz_payload = task_payload.get("payload")
            if not isinstance(biz_payload, dict):
                biz_payload = task_payload

            result = await task.run(biz_payload)
            status = str(result.get("status", "success")).lower() if isinstance(result, dict) else "success"

            if status == "success":
                await self._state_manager.mark_success(task_run_id, last_checkpoint="finished")
                await self._sync_feature_status_if_needed(task_payload, self.ACCOUNT_SYNC_STATUS_SUCCESS)
                return
            if status == "cancelled":
                await self._state_manager.mark_cancelled(task_run_id, reason=result.get("error_message"))
                await self._sync_feature_status_if_needed(task_payload, self.ACCOUNT_SYNC_STATUS_FAILED)
                return
            if status == "timeout":
                await self._state_manager.mark_timeout(task_run_id, reason=result.get("error_message"))
                await self._sync_feature_status_if_needed(task_payload, self.ACCOUNT_SYNC_STATUS_FAILED)
                return

            error_code = result.get("error_code") if isinstance(result, dict) else None
            error_message = result.get("error_message") if isinstance(result, dict) else "Task returned failure status"
            await self._mark_failed_and_schedule_retry(
                task_run_id=task_run_id,
                root_run_id=task_record.root_run_id,
                task_payload=task_payload,
                error_code=error_code,
                error_message=error_message,
                last_checkpoint="task_result_failed",
            )
        except asyncio.CancelledError:
            await self._state_manager.mark_cancelled(task_run_id, reason="Task execution cancelled")
            await self._sync_feature_status_if_needed(task_payload, self.ACCOUNT_SYNC_STATUS_FAILED)
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("%s 任务执行异常 | task_run_id=%s", LOG_PREFIX, task_run_id)
            await self._mark_failed_and_schedule_retry(
                task_run_id=task_run_id,
                root_run_id=task_record.root_run_id,
                task_payload=task_payload,
                error_code="UNEXPECTED_ERROR",
                error_message=str(exc),
                last_checkpoint="task_exception",
            )
        finally:
            await self._heartbeat_service.stop(task_run_id)

    async def _mark_failed_and_schedule_retry(
        self,
        *,
        task_run_id: UUID,
        root_run_id: UUID,
        task_payload: dict[str, Any],
        error_code: str | None,
        error_message: str | None,
        last_checkpoint: str,
    ) -> None:
        next_run_id = await self._state_manager.mark_failed_and_schedule_retry(
            task_run_id=task_run_id,
            error_code=error_code,
            error_message=error_message,
            last_checkpoint=last_checkpoint,
            retry_delay_seconds=self._retry_delay_seconds,
            retry_max_attempts=self._retry_max_attempts,
        )
        if next_run_id is None:
            await self._sync_feature_status_if_needed(task_payload, self.ACCOUNT_SYNC_STATUS_FAILED)
            return

        if not task_payload:
            logger.warning("%s 已创建重试 run，但缺少 payload 无法重新入队 | next_run_id=%s", LOG_PREFIX, next_run_id)
            await self._sync_feature_status_if_needed(task_payload, self.ACCOUNT_SYNC_STATUS_FAILED)
            return

        await self._sync_feature_status_if_needed(task_payload, self.ACCOUNT_SYNC_STATUS_WAITING)

        timer = asyncio.create_task(
            self._enqueue_retry_message_after_delay(
                next_run_id=next_run_id,
                root_run_id=root_run_id,
                task_payload=task_payload,
            )
        )
        self._retry_enqueue_tasks.add(timer)
        timer.add_done_callback(self._on_retry_enqueue_done)

    async def _enqueue_retry_message_after_delay(
        self,
        *,
        next_run_id: UUID,
        root_run_id: UUID,
        task_payload: dict[str, Any],
    ) -> None:
        delay_seconds = max(0, self._retry_delay_seconds)
        if delay_seconds:
            await asyncio.sleep(delay_seconds)

        created_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        fields = {
            "task_run_id": str(next_run_id),
            "root_run_id": str(root_run_id),
            "payload": json.dumps(task_payload, separators=(",", ":"), ensure_ascii=False),
            "created_at": created_at,
        }
        await self._stream_client.add_task_message(stream=self._settings.task_stream, fields=fields)
        logger.info("%s 重试任务已重新入队 | task_run_id=%s", LOG_PREFIX, next_run_id)

    def _on_retry_enqueue_done(self, task: asyncio.Task[None]) -> None:
        self._retry_enqueue_tasks.discard(task)
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            return
        if exc:
            logger.exception("%s 重试入队任务异常退出", LOG_PREFIX)

    async def _log_sink(self, payload: dict[str, Any]) -> None:
        await self._stream_client.add_log_event(
            stream=self._settings.task_log_stream,
            event_payload=payload,
            maxlen=self._settings.task_log_stream_maxlen,
        )

    def _build_task_log_sink(self, *, task_run_id: UUID, root_run_id: UUID):
        async def sink(payload: dict[str, Any]) -> None:
            enriched = dict(payload)
            enriched.setdefault("task_run_id", str(task_run_id))
            enriched.setdefault("taskRunId", str(task_run_id))
            enriched.setdefault("root_run_id", str(root_run_id))
            enriched.setdefault("rootRunId", str(root_run_id))
            await self._log_sink(enriched)

        return sink

    async def _ack_message(self, message: TaskStreamMessage) -> None:
        await self._stream_client.ack(
            stream=self._settings.task_stream,
            group=self._settings.task_stream_group,
            message_id=message.message_id,
        )

    @staticmethod
    def _parse_task_run_id(raw: str | None) -> UUID | None:
        if not raw:
            return None
        try:
            return UUID(raw)
        except ValueError:
            return None

    @staticmethod
    def _extract_task_payload(fields: dict[str, str]) -> dict[str, Any]:
        raw_payload = fields.get("payload")
        if raw_payload:
            try:
                parsed = json.loads(raw_payload)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:  # noqa: BLE001
                return {}

        module = fields.get("module")
        action = fields.get("action")
        if module and action:
            return {"module": module, "action": action}
        return {}

    @property
    def _consumer_name(self) -> str:
        consumer = self._settings.task_stream_consumer.strip()
        if consumer:
            return consumer
        return self._settings.worker_instance_id

    @property
    def _retry_delay_seconds(self) -> int:
        if self._runtime is not None:
            return self._runtime.retry_delay_seconds
        return self._settings.retry_delay_seconds

    @property
    def _retry_max_attempts(self) -> int:
        if self._runtime is not None:
            return self._runtime.retry_max_attempts
        return self._settings.retry_max_attempts

    async def _sync_feature_status_if_needed(self, task_payload: dict[str, Any], sync_status: int) -> None:
        if str(task_payload.get("action") or "").strip() != self.FEATURE_SYNC_ACTION:
            return

        account_id = self._extract_google_account_id(task_payload)
        if account_id is None:
            return

        try:
            await self._state_manager.set_google_account_sync_status(account_id, sync_status)
        except Exception:  # noqa: BLE001
            logger.exception(
                "%s 更新 Google 账号同步状态失败 | account_id=%s | sync_status=%s",
                LOG_PREFIX,
                account_id,
                sync_status,
            )

    @staticmethod
    def _extract_google_account_id(task_payload: dict[str, Any]) -> int | None:
        biz_payload = task_payload.get("payload")
        if not isinstance(biz_payload, dict):
            biz_payload = task_payload

        raw_account_id = (
            biz_payload.get("google_account_id")
            or biz_payload.get("googleAccountId")
            or biz_payload.get("account_id")
            or biz_payload.get("accountId")
        )
        if raw_account_id is None:
            return None
        try:
            return int(raw_account_id)
        except (TypeError, ValueError):
            return None
