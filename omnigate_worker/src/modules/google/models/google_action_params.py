"""Google 相关 Action 入参模型。"""

from pydantic import BaseModel, Field


class GoogleAuthParams(BaseModel):
    """Google 登录动作入参。"""

    # Google 账号（邮箱）
    google_account: str = Field(min_length=1)
    # Google 密码（后续步骤会使用）
    password: str = Field(min_length=1)
    # 2FA 信息（可选）
    twofa: str = ""


class GoogleFamilyInviteParams(BaseModel):
    """Google 家庭组邀请动作入参。"""

    # 被邀请邮箱
    target_email: str = Field(
        min_length=6,
        max_length=100,
        pattern=r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
    )
