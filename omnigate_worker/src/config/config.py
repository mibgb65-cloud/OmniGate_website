"""应用配置模块：统一读取 .env 与环境变量。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """全局配置对象。"""

    # PostgreSQL 异步连接串（SQLAlchemy + asyncpg）
    DB_URL: str = "postgresql+asyncpg://user:password@localhost:5432/account_db"
    # Redis 连接串
    REDIS_URL: str = "redis://localhost:6379/0"
    # Redis 队列名
    REDIS_QUEUE: str = "account_tasks"
    # Worker 最大重试次数（仅额外重试次数，不含首次执行）
    TASK_MAX_RETRIES: int = 2
    # 重试基础延迟秒数（第 n 次重试延迟 = 基础延迟 * n）
    RETRY_BASE_DELAY_SECONDS: int = 5
    # 日志级别
    LOG_LEVEL: str = "INFO"
    # 是否无头模式启动浏览器
    BROWSER_HEADLESS: bool = True
    # 浏览器启动参数（逗号分隔），例如：
    # --disable-blink-features=AutomationControlled,--window-size=1366,768
    BROWSER_ARGS: str = ""
    # 代理地址（可选），例如：http://127.0.0.1:7890
    BROWSER_PROXY: str | None = None
    # 浏览器用户数据目录（可选），用于保持登录态
    BROWSER_USER_DATA_DIR: str | None = None
    # 是否启用 sandbox（Linux 环境常用）
    BROWSER_SANDBOX: bool = True
    # 浏览器语言（可选），例如：en-US
    BROWSER_LANG: str | None = "en-US"

    # 从项目根目录的 .env 读取配置，忽略未定义字段
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """返回单例配置，避免重复解析环境变量。"""
    return Settings()
