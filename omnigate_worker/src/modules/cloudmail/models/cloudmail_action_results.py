"""CloudMail 相关 Action 返回结果模型。"""

from pydantic import BaseModel, ConfigDict, Field


class CloudMailAuthResult(BaseModel):
    """登录返回结果。"""

    cloudmail_token: str | None = None


class CloudMailEmailItemResult(BaseModel):
    """单封邮件结果。"""

    model_config = ConfigDict(populate_by_name=True)

    email_id: int | None = Field(default=None, alias="emailId")
    send_email: str | None = Field(default=None, alias="sendEmail")
    send_name: str | None = Field(default=None, alias="sendName")
    subject: str | None = None
    to_email: str | None = Field(default=None, alias="toEmail")
    to_name: str | None = Field(default=None, alias="toName")
    create_time: str | None = Field(default=None, alias="createTime")
    type: int | None = None
    content: str | None = None
    text: str | None = None
    is_del: int | None = Field(default=None, alias="isDel")


class CloudMailReadEmailResult(BaseModel):
    """邮件列表读取结果。"""

    emails: list[CloudMailEmailItemResult] = Field(default_factory=list)

