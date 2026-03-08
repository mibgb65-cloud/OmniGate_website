"""cloudmail 相关 Action 入参模型。"""

from pydantic import BaseModel, Field


class CloudMailAuthParams(BaseModel):
    """cloudmail 登录动作入参。"""

    # cloudmail 账号（邮箱）
    cloudmail_account: str = Field(min_length=1)
    # cloudmail 密码
    password: str = Field(min_length=1)
    # cloudmail 登录网址
    auth_url: str = Field(min_length=1)


class CloudMailReadEmailParams(BaseModel):
    """cloudmail 邮件查询入参。"""

    # cloudmail 认证token
    cloudmail_token: str = Field(min_length=1)
    # cloudmail 收件人邮箱，支持模糊
    cloudmail_toEmail: str = Field(min_length=1)
    # cloudmail 发件人名字，支持模糊
    cloudmail_sendName: str | None = Field(default=None, min_length=1)
    # cloudmail 邮件主题，支持模糊
    cloudmail_subject: str | None = Field(default=None, min_length=1)
    # cloudmail 邮件类型 （0 收件，1 发件，空 全部）
    cloudmail_type: str | int | None = None
    # cloudmail 服务地址，用于拼接 /api/public/emailList
    auth_url: str | None = Field(default=None, min_length=1)

