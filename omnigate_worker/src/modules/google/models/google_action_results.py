"""Google 相关 Action 返回结果模型。"""

from typing import Literal

from pydantic import BaseModel, Field


class GoogleSubscriptionResult(BaseModel):
    """订阅页解析结果。"""

    found_onepro: bool
    subscription_status: Literal["ACTIVE", "INACTIVE", "UNKNOWN"]
    expires_at_text: str | None = None
    subscription_name: str | None = None
    subscription_details: list[str] | None = None
    source_url: str | None = None


class GoogleInviteResult(BaseModel):
    """邀请页解析结果。"""

    has_referral_invite: bool
    invite_title: str | None = None
    referral_link: str | None = None
    invitation_usage_text: str | None = None
    invitations_used: int | None = None
    invitations_total: int | None = None
    invite_source_url: str | None = None


class GoogleSubscriptionAndInviteResult(BaseModel):
    """订阅页 + 邀请页合并结果。"""

    found_onepro: bool
    subscription_status: Literal["ACTIVE", "INACTIVE", "UNKNOWN"]
    expires_at_text: str | None = None
    subscription_name: str | None = None
    subscription_details: list[str] | None = None
    source_url: str | None = None

    has_referral_invite: bool
    invite_title: str | None = None
    referral_link: str | None = None
    invitation_usage_text: str | None = None
    invitations_used: int | None = None
    invitations_total: int | None = None
    invite_source_url: str | None = None


class GoogleFamilyMemberInfo(BaseModel):
    """家庭组成员信息。"""

    member_name: str | None = None
    member_role: str | None = None
    member_email: str | None = None
    member_href: str | None = None


class GoogleFamilyCheckResult(BaseModel):
    """家庭组检查结果。"""

    source_url: str
    family_group_opened: bool
    has_get_started: bool
    can_send_invitations: bool
    invitations_left: int | None = None
    invitations_text: str | None = None
    member_count: int = 0
    members: list[GoogleFamilyMemberInfo] = Field(default_factory=list)


class GoogleFamilyInviteResult(BaseModel):
    """家庭组邀请动作结果。"""

    success: bool
    message: str
    details: str | None = None


class GoogleStudentEligibilityResult(BaseModel):
    """Google 学生资格检测结果。"""

    status: Literal["已订阅", "已认证/未订阅", "未订阅 (需验证)", "未知状态"]
    eligibility_link: str | None = None
    source_url: str | None = None
    current_url: str | None = None
    retries: int = 0
