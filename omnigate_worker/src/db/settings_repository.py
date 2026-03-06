from __future__ import annotations

import asyncpg


class SystemSettingsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_many(self, keys: list[str]) -> dict[str, str]:
        if not keys:
            return {}
        query = """
            SELECT key, value
            FROM system_settings
            WHERE key = ANY($1::varchar[])
        """
        rows = await self._pool.fetch(query, keys)
        return {row["key"]: row["value"] for row in rows}
