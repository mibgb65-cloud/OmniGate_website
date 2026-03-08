from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(slots=True, frozen=True)
class GithubAccountCredential:
    """GitHub 登录所需的已解密账号实体。"""

    account_id: int
    username: str
    email: str
    password: str
    totp_secret: str


@dataclass(slots=True, frozen=True)
class GithubRepoIdentity:
    """规范化后的 GitHub 仓库标识。"""

    repo_url: str
    repo_owner: str
    repo_name: str

    @property
    def repo_full_name(self) -> str:
        return f"{self.repo_owner}/{self.repo_name}"

    @classmethod
    def from_url(cls, repo_url: str) -> "GithubRepoIdentity":
        raw = (repo_url or "").strip()
        if not raw:
            raise ValueError("repo_url 不能为空")

        parsed = urlsplit(raw)
        host = (parsed.netloc or "").strip().lower()
        if host not in {"github.com", "www.github.com"}:
            raise ValueError(f"repo_url 不是合法的 GitHub 仓库地址: {repo_url}")

        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            raise ValueError(f"repo_url 缺少 owner/repo 信息: {repo_url}")

        owner = parts[0].strip()
        repo = parts[1].strip().removesuffix(".git")
        if not owner or not repo:
            raise ValueError(f"repo_url 缺少有效的 owner/repo 信息: {repo_url}")

        return cls(
            repo_url=f"https://github.com/{owner}/{repo}",
            repo_owner=owner,
            repo_name=repo,
        )
