from __future__ import annotations

import random
import string
import secrets

import asyncpg

from src.db import ChatGptAccountPersistence, SystemSettingsRepository


_PASSWORD_SYMBOLS = "!@#$%&*?"
_PASSWORD_FILLER_POOL = string.ascii_letters * 3 + string.digits * 2
_EMAIL_LOCAL_ALPHABET = string.ascii_lowercase + string.digits
_FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
]
_MIDDLE_NAMES = [
    "Allen", "Grace", "Marie", "Lee", "Ray", "Rose", "Jean", "Ann",
    "Scott", "Claire", "Dean", "Faith", "Blake", "Jane", "Paul", "Mae",
    "Cole", "Hope", "Louise", "Jack", "Brooke", "June", "Reed", "Kate",
    "Ross", "Eve", "Lane", "Skye", "Grant", "Pearl", "Chase", "Faye",
    "Quinn", "Ruth", "Bryce", "Maeve", "Tate", "Joy", "Finn", "Sage",
]
_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
]


def generate_random_name():
    """生成随机的英文全名（名 + 中间名 + 姓）"""
    first_name = random.choice(_FIRST_NAMES)
    middle_name = random.choice(_MIDDLE_NAMES)
    last_name = random.choice(_LAST_NAMES)

    return f"{first_name} {middle_name} {last_name}"


def generate_random_password(min_length=13, max_length=17):
    """
    生成更偏字母数字风格的随机密码，长度在 min_length 和 max_length 之间随机。
    约束：
    - 首位和末位必须是字母；
    - 中间仅保留 1~2 个符号，避免符号过多；
    - 至少包含 1 个小写字母、1 个大写字母、1 个数字、1 个符号。
    默认参数满足：大于12 (即>=13)，小于18 (即<=17)。
    """
    # 严格的边界条件校验
    if min_length <= 12:
        raise ValueError("错误：密码最小长度必须大于 12。")
    if max_length >= 18:
        raise ValueError("错误：密码最大长度必须小于 18。")
    if min_length > max_length:
        raise ValueError("错误：密码最小长度不能大于最大长度。")

    current_length = random.randint(min_length, max_length)
    symbol_count = 1 if current_length <= 15 else 2
    middle_length = current_length - 2
    required_middle_chars = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
    ]
    required_middle_chars.extend(
        secrets.choice(_PASSWORD_SYMBOLS) for _ in range(symbol_count)
    )

    if len(required_middle_chars) > middle_length:
        raise ValueError("错误：密码长度不足以满足复杂度要求。")

    filler_count = middle_length - len(required_middle_chars)
    middle_chars = [
        *required_middle_chars,
        *(secrets.choice(_PASSWORD_FILLER_POOL) for _ in range(filler_count)),
    ]
    random.SystemRandom().shuffle(middle_chars)

    first_char = secrets.choice(string.ascii_letters)
    last_char = secrets.choice(string.ascii_letters)
    return f"{first_char}{''.join(middle_chars)}{last_char}"


def generate_random_email_prefix(length: int = 12, *, preferred_name: str | None = None) -> str:
    """生成随机邮箱前缀，优先包含名字片段，只包含小写字母和数字。"""
    if length < 6:
        raise ValueError("错误：邮箱前缀长度不能小于 6。")

    name_based_prefix = _build_name_based_email_prefix(preferred_name, length)
    if name_based_prefix:
        return name_based_prefix

    first_char = secrets.choice(string.ascii_lowercase)
    remaining = "".join(secrets.choice(_EMAIL_LOCAL_ALPHABET) for _ in range(length - 1))
    return f"{first_char}{remaining}"


async def generate_random_email(
    *,
    db_pool: asyncpg.Pool | None = None,
    settings_repository: SystemSettingsRepository | None = None,
    account_persistence: ChatGptAccountPersistence | None = None,
    preferred_name: str | None = None,
    prefix_length: int = 12,
    max_attempts: int = 20,
) -> str:
    """
    生成随机邮箱地址。

    邮箱前缀优先包含名字片段并追加随机尾巴，邮箱后缀从 `system_settings` 中的
    `chatgpt.registration_email_suffix` 读取。
    """
    if settings_repository is None:
        if db_pool is None:
            raise ValueError("错误：db_pool 或 settings_repository 至少需要传一个。")
        settings_repository = SystemSettingsRepository(db_pool)
    if account_persistence is None:
        if db_pool is None:
            raise ValueError("错误：db_pool 或 account_persistence 至少需要传一个。")
        account_persistence = ChatGptAccountPersistence(db_pool)
    if max_attempts <= 0:
        raise ValueError("错误：max_attempts 必须大于 0。")

    email_suffix = await settings_repository.get_chatgpt_registration_email_suffix()
    normalized_suffix = _normalize_email_suffix(email_suffix)
    for _ in range(max_attempts):
        prefix = generate_random_email_prefix(prefix_length, preferred_name=preferred_name)
        candidate_email = f"{prefix}@{normalized_suffix}"
        if not await account_persistence.email_exists(candidate_email):
            return candidate_email

    raise RuntimeError(f"生成唯一 ChatGPT 注册邮箱失败，已重试 {max_attempts} 次")


def _build_name_based_email_prefix(name: str | None, length: int) -> str:
    """按名字生成邮箱前缀，并保留少量随机尾巴提升唯一性。"""
    normalized_tokens = _extract_name_tokens(name)
    if not normalized_tokens:
        return ""

    base = "".join(normalized_tokens)
    if not base:
        return ""

    reserved_tail_length = min(4, max(2, length // 3))
    max_core_length = max(1, length - reserved_tail_length)
    core = base[:max_core_length]
    tail_length = length - len(core)
    tail = "".join(secrets.choice(_EMAIL_LOCAL_ALPHABET) for _ in range(tail_length))
    return f"{core}{tail}"


def _extract_name_tokens(name: str | None) -> list[str]:
    """从姓名中提取可用于邮箱前缀的纯字母片段。"""
    raw_text = str(name or "").strip().lower()
    if not raw_text:
        return []

    normalized = "".join(char if char in string.ascii_lowercase else " " for char in raw_text)
    return [token for token in normalized.split() if token]


def _normalize_email_suffix(value: str | None) -> str:
    """把数据库中的邮箱后缀归一成可直接拼接的域名部分。"""
    normalized = str(value or "").strip().lower()
    if normalized.startswith("@"):
        normalized = normalized[1:]
    if not normalized:
        raise RuntimeError("system_settings 缺少 chatgpt.registration_email_suffix 配置")
    if "@" in normalized:
        raise ValueError("chatgpt.registration_email_suffix 只能保存邮箱域名，不要带 @ 前缀")
    if "." not in normalized:
        raise ValueError("chatgpt.registration_email_suffix 格式不正确，至少应包含一个点")
    if any(char.isspace() for char in normalized):
        raise ValueError("chatgpt.registration_email_suffix 不能包含空白字符")
    return normalized


def main():
    num_to_generate = 5
    
    print(f"--- 正在生成 {num_to_generate} 组随机信息 ---")
    print(f"{'英文名':<20} | {'随机密码 (13-17位)':<20}")
    print("-" * 45)
    
    for _ in range(num_to_generate):
        name = generate_random_name()
        # 调用时如果不传参，将使用默认的 13 到 17 之间随机
        try:
            password = generate_random_password()
            print(f"{name:<20} | {password:<20}")
        except ValueError as e:
            print(f"生成失败: {e}")
            break


if __name__ == "__main__":
    main()
