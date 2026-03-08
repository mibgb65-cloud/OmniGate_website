"""对外暴露 worker DB 层常用对象，避免业务代码到处写具体文件路径。"""

from src.db.chatgpt_account_persistence import ChatGptAccountPersistence
from src.db.database import Database
from src.db.google_account_persistence import GoogleAccountPersistence
from src.db.google_account_repository import GoogleAccountCredentialRecord, GoogleAccountRepository
from src.db.settings_repository import CloudMailAuthSettingRecord, SystemSettingsRepository
from src.db.task_repository import TaskRunRecord, TaskRunRepository

# 这里集中 re-export，业务层只需要 `from src.db import ...` 即可。
__all__ = [
    "ChatGptAccountPersistence",
    "CloudMailAuthSettingRecord",
    "Database",
    "GoogleAccountCredentialRecord",
    "GoogleAccountPersistence",
    "GoogleAccountRepository",
    "SystemSettingsRepository",
    "TaskRunRecord",
    "TaskRunRepository",
]
