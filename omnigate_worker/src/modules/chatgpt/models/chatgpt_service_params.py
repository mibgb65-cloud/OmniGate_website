"""ChatGPT 相关 Service 入参模型。"""

from pydantic import BaseModel, Field


class BatchRegisterChatGptAccountsParams(BaseModel):
    """批量自动注册 ChatGPT 账号的服务入参。"""

    signup_count: int = Field(gt=0, le=100)
