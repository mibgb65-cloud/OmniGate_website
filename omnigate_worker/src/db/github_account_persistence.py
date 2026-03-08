"""GitHub 账号相关落库能力。"""

from __future__ import annotations

import asyncpg

from src.utils import AesTypeHandlerCompat


class GithubAccountPersistence:
    """负责写回 GitHub token 与仓库交互记录。"""

    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        encryptor: AesTypeHandlerCompat | None = None,
    ) -> None:
        self._pool = pool
        self._encryptor = encryptor or AesTypeHandlerCompat()

    async def update_access_token(
        self,
        *,
        account_id: int,
        access_token: str,
        token_note: str | None = None,
    ) -> None:
        """更新账号的 GitHub Personal Access Token。"""

        normalized_token = (access_token or "").strip()
        normalized_note = self._normalize_optional_text(token_note)
        if not normalized_token:
            raise ValueError("access_token 不能为空")

        encrypted_token = self._encryptor.encrypt_base64(normalized_token)
        status = await self._pool.execute(
            """
            UPDATE acc_github_base
            SET access_token = $2,
                access_token_note = $3,
                updated_at = now()
            WHERE id = $1
              AND deleted = 0
            """,
            int(account_id),
            encrypted_token,
            normalized_note,
        )
        if status.endswith("0"):
            raise ValueError(f"GitHub 账号不存在或已删除: account_id={account_id}")

    async def upsert_repo_interaction(
        self,
        *,
        account_id: int,
        repo_owner: str,
        repo_name: str,
        repo_url: str,
        starred: bool | None = None,
        forked: bool | None = None,
        watched: bool | None = None,
        followed: bool | None = None,
    ) -> None:
        """按账号 + 仓库维度写入或更新交互记录。"""

        normalized_owner = self._normalize_required_text(repo_owner, field_name="repo_owner")
        normalized_name = self._normalize_required_text(repo_name, field_name="repo_name")
        normalized_url = self._normalize_required_text(repo_url, field_name="repo_url")

        star_value = self._flag_to_db(starred)
        fork_value = self._flag_to_db(forked)
        watch_value = self._flag_to_db(watched)
        follow_value = self._flag_to_db(followed)

        await self._pool.execute(
            """
            INSERT INTO acc_github_repo_interaction (
                account_id,
                repo_owner,
                repo_name,
                repo_url,
                starred,
                starred_at,
                forked,
                forked_at,
                watched,
                watched_at,
                followed,
                followed_at,
                deleted,
                created_at,
                updated_at
            )
            VALUES (
                $1,
                $2,
                $3,
                $4,
                COALESCE($5, 0),
                CASE WHEN $5 = 1 THEN now() ELSE NULL END,
                COALESCE($6, 0),
                CASE WHEN $6 = 1 THEN now() ELSE NULL END,
                COALESCE($7, 0),
                CASE WHEN $7 = 1 THEN now() ELSE NULL END,
                COALESCE($8, 0),
                CASE WHEN $8 = 1 THEN now() ELSE NULL END,
                0,
                now(),
                now()
            )
            ON CONFLICT (account_id, repo_owner, repo_name, deleted) DO UPDATE SET
                repo_url = EXCLUDED.repo_url,
                starred = COALESCE($5, acc_github_repo_interaction.starred),
                starred_at = CASE
                    WHEN $5 = 1 THEN COALESCE(acc_github_repo_interaction.starred_at, now())
                    WHEN $5 = 0 THEN NULL
                    ELSE acc_github_repo_interaction.starred_at
                END,
                forked = COALESCE($6, acc_github_repo_interaction.forked),
                forked_at = CASE
                    WHEN $6 = 1 THEN COALESCE(acc_github_repo_interaction.forked_at, now())
                    WHEN $6 = 0 THEN NULL
                    ELSE acc_github_repo_interaction.forked_at
                END,
                watched = COALESCE($7, acc_github_repo_interaction.watched),
                watched_at = CASE
                    WHEN $7 = 1 THEN COALESCE(acc_github_repo_interaction.watched_at, now())
                    WHEN $7 = 0 THEN NULL
                    ELSE acc_github_repo_interaction.watched_at
                END,
                followed = COALESCE($8, acc_github_repo_interaction.followed),
                followed_at = CASE
                    WHEN $8 = 1 THEN COALESCE(acc_github_repo_interaction.followed_at, now())
                    WHEN $8 = 0 THEN NULL
                    ELSE acc_github_repo_interaction.followed_at
                END,
                updated_at = now()
            """,
            int(account_id),
            normalized_owner,
            normalized_name,
            normalized_url,
            star_value,
            fork_value,
            watch_value,
            follow_value,
        )

    @staticmethod
    def _flag_to_db(value: bool | None) -> int | None:
        if value is None:
            return None
        return 1 if value else 0

    @staticmethod
    def _normalize_required_text(value: str | None, *, field_name: str) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError(f"{field_name} 不能为空")
        return text

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        text = (value or "").strip()
        return text or None
