from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ResponseError


logger = logging.getLogger(__name__)
LOG_PREFIX = "[RedisStream]"


@dataclass(slots=True)
class TaskStreamMessage:
    stream: str
    message_id: str
    fields: dict[str, str]

    def get_json_payload(self) -> dict[str, Any]:
        payload = self.fields.get("payload")
        if not payload:
            return {}
        try:
            parsed = json.loads(payload)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


class RedisStreamClient:
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._redis: Redis | None = None
        self._supports_xautoclaim: bool | None = None

    @property
    def redis(self) -> Redis:
        if self._redis is None:
            raise RuntimeError("Redis client is not initialized. Call connect() first.")
        return self._redis

    async def connect(self) -> None:
        if self._redis is None:
            self._redis = Redis.from_url(self._redis_url, decode_responses=True)
            await self._redis.ping()

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def ensure_group(self, *, stream: str, group: str) -> None:
        try:
            await self.redis.xgroup_create(name=stream, groupname=group, id="0", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def read_group(
        self,
        *,
        stream: str,
        group: str,
        consumer: str,
        count: int,
        block_ms: int,
    ) -> list[TaskStreamMessage]:
        count = max(1, count)
        raw_items = await self.redis.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={stream: ">"},
            count=count,
            block=max(0, block_ms),
        )
        messages: list[TaskStreamMessage] = []
        for stream_name, entries in raw_items:
            for message_id, fields in entries:
                messages.append(
                    TaskStreamMessage(
                        stream=stream_name,
                        message_id=message_id,
                        fields={k: str(v) for k, v in fields.items()},
                    )
                )
        return messages

    async def auto_claim(
        self,
        *,
        stream: str,
        group: str,
        consumer: str,
        min_idle_ms: int,
        start_id: str = "0-0",
        count: int = 10,
    ) -> tuple[str, list[TaskStreamMessage]]:
        if self._supports_xautoclaim is False:
            return start_id, []

        try:
            response = await self.redis.xautoclaim(
                name=stream,
                groupname=group,
                consumername=consumer,
                min_idle_time=max(0, min_idle_ms),
                start_id=start_id,
                count=max(1, count),
            )
            self._supports_xautoclaim = True
        except ResponseError as exc:
            if self._is_xautoclaim_unsupported(exc):
                self._supports_xautoclaim = False
                logger.warning(
                    "%s 当前 Redis 不支持 XAUTOCLAIM，已关闭 pending message 自动认领 | 建议=升级到 Redis 6.2+",
                    LOG_PREFIX,
                )
                return start_id, []
            raise
        if not response:
            return start_id, []

        next_start = str(response[0]) if len(response) > 0 else start_id
        entries = response[1] if len(response) > 1 and isinstance(response[1], list) else []

        messages: list[TaskStreamMessage] = []
        for message_id, fields in entries:
            messages.append(
                TaskStreamMessage(
                    stream=stream,
                    message_id=str(message_id),
                    fields={k: str(v) for k, v in fields.items()},
                )
            )
        return next_start, messages

    @staticmethod
    def _is_xautoclaim_unsupported(exc: ResponseError) -> bool:
        message = str(exc).strip().lower()
        return "unknown command" in message and "xautoclaim" in message

    async def ack(self, *, stream: str, group: str, message_id: str) -> None:
        await self.redis.xack(stream, group, message_id)

    async def add_task_message(self, *, stream: str, fields: dict[str, str]) -> str:
        return await self.redis.xadd(stream, fields)

    async def add_log_event(
        self,
        *,
        stream: str,
        event_payload: dict[str, Any],
        maxlen: int,
    ) -> None:
        fields: dict[str, str] = {}
        for key, value in event_payload.items():
            if isinstance(value, dict):
                fields[key] = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
            else:
                fields[key] = str(value)
        await self.redis.xadd(stream, fields, maxlen=max(1, maxlen), approximate=True)
