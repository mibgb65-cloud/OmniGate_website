from __future__ import annotations

import asyncpg


def normalize_postgres_dsn(raw_dsn: str) -> str:
    """把 SQLAlchemy 风格 DSN 转成 asyncpg 可直接识别的格式。"""

    if raw_dsn.startswith("postgresql+asyncpg://"):
        return raw_dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    return raw_dsn


class Database:
    """包装 asyncpg 连接池的极薄适配层。"""

    def __init__(self, dsn: str) -> None:
        # 配置可能来自后端或环境变量，先在入口统一做一次 DSN 规范化。
        self._dsn = normalize_postgres_dsn(dsn)
        self._pool: asyncpg.Pool | None = None

    @property
    def pool(self) -> asyncpg.Pool:
        """返回已初始化的连接池；如果还没 connect，直接报错提醒调用方。"""

        if self._pool is None:
            raise RuntimeError("Database pool is not initialized. Call connect() first.")
        return self._pool

    async def connect(self) -> None:
        """懒加载创建连接池，多次调用不会重复创建。"""

        if self._pool is None:
            self._pool = await asyncpg.create_pool(dsn=self._dsn, min_size=1, max_size=10)

    async def close(self) -> None:
        """关闭连接池并清空引用，便于 worker 优雅退出。"""

        if self._pool is not None:
            await self._pool.close()
            self._pool = None
