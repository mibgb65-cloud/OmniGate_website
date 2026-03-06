"""Google 相关 Service 入参模型。"""

from pydantic import BaseModel, Field


class GetGoogleAccountFeatureByAccountIdParams(BaseModel):
    """根据账号ID获取 Google 账号功能状态的服务入参。"""

    # 谷歌账号主键ID（对应 google_account.id）
    google_account_id: int = Field(gt=0)


class InviteGoogleFamilyMemberByAccountIdParams(BaseModel):
    """根据母号账号ID邀请指定邮箱加入家庭组。"""

    # 家庭组母号的谷歌账号主键ID（对应 google_account.id）
    google_account_id: int = Field(gt=0)
    # 被拉账号邮箱
    invited_account_email: str = Field(
        min_length=6,
        max_length=100,
        pattern=r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
    )


class GetGoogleAccountStudentEligibilityByAccountIdParams(BaseModel):
    """根据账号ID获取 Google 学生资格查询链接的服务入参。"""

    # 谷歌账号主键ID（对应 google_account.id）
    google_account_id: int = Field(gt=0)
