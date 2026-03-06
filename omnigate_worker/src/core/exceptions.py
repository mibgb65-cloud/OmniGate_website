"""自定义异常定义。"""

class AppError(Exception):
    """应用基础异常。"""


class FetchError(AppError):
    """抓取数据失败时抛出。"""


class DBDropError(AppError):
    """数据库操作异常时抛出。"""
