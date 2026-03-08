"""CloudMail 相关 Service 入参模型。"""

from pydantic import BaseModel, Field


class GetChatGptVerificationCodeParams(BaseModel):
    """获取 ChatGPT 注册/登录验证码的服务入参。"""

    # 收件人邮箱，至少要有它才能定位到目标验证码邮件。
    cloudmail_toEmail: str = Field(min_length=1)
    # 发件人名称，可选，用于进一步缩小邮件范围。
    cloudmail_sendName: str | None = Field(default=None, min_length=1)
    # 邮件主题，可选，用于进一步缩小邮件范围。
    cloudmail_subject: str | None = Field(default=None, min_length=1)
    # 邮件类型：0 收件，1 发件，空表示不限制。
    cloudmail_type: str | int | None = 0
