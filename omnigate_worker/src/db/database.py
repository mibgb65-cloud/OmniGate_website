from __future__ import annotations

import asyncpg


def normalize_postgres_dsn(raw_dsn: str) -> str:
    if raw_dsn.startswith("postgresql+asyncpg://"):
        return raw_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    return raw_dsn


class Database:
    def __init__(self, dsn: str) -> None:
        self._dsn = normalize_postgres_dsn(dsn)
        self._pool: asyncpg.Pool | None = None

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized. Call connect() first.")
        return self._pool

    async def connect(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(dsn=self._dsn, min_size=1, max_size=10)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
