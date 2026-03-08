"""GitHub 相关 Service 入参模型。"""

from pydantic import BaseModel, Field, field_validator


class GenerateGithubTokenByAccountIdParams(BaseModel):
    """根据账号 ID 生成 GitHub PAT 的服务入参。"""

    github_account_id: int = Field(gt=0)


class StarGithubRepoByAccountIdParams(BaseModel):
    """根据账号 ID 登录并为指定仓库点 Star。"""

    github_account_id: int = Field(gt=0)
    repo_url: str = Field(min_length=18, max_length=1024)

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("repo_url 不能为空")
        return normalized
