from __future__ import annotations

import random
import string
import secrets

import asyncpg

from src.db import SystemSettingsRepository


def generate_random_name():
    """生成随机的英文名字（已扩充词库）"""
    first_names = [
        "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", 
        "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", 
        "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa", 
        "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
        "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle"
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", 
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", 
        "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", 
        "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", 
        "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores"
    ]
    
    first_name = random.choice(first_names)
    last_name = random.choice(last_names)
    
    return f"{first_name} {last_name}"


def generate_random_password(min_length=13, max_length=17):
    """
    生成高强度的随机密码，长度在 min_length 和 max_length 之间随机。
    默认参数满足：大于12 (即>=13)，小于18 (即<=17)。
    """
    # 严格的边界条件校验
    if min_length <= 12:
        raise ValueError("错误：密码最小长度必须大于 12。")
    if max_length >= 18:
        raise ValueError("错误：密码最大长度必须小于 18。")
    if min_length > max_length:
        raise ValueError("错误：密码最小长度不能大于最大长度。")

    # 随机决定当前生成密码的具体长度
    current_length = random.randint(min_length, max_length)

    # 定义密码的字符集：大小写字母、数字、特殊符号
    alphabet = string.ascii_letters + string.digits + string.punctuation
    
    # 循环生成，直到密码满足所有复杂性要求
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(current_length))
        
        # 必须包含至少1个小写、1个大写、1个数字、1个特殊字符
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in string.punctuation for c in password)):
            break
            
    return password


def generate_random_email_prefix(length: int = 12) -> str:
    """生成随机邮箱前缀，只包含小写字母和数字。"""
    if length < 6:
        raise ValueError("错误：邮箱前缀长度不能小于 6。")

    first_char = secrets.choice(string.ascii_lowercase)
    alphabet = string.ascii_lowercase + string.digits
    remaining = "".join(secrets.choice(alphabet) for _ in range(length - 1))
    return f"{first_char}{remaining}"


async def generate_random_email(
    *,
    db_pool: asyncpg.Pool | None = None,
    settings_repository: SystemSettingsRepository | None = None,
    prefix_length: int = 12,
) -> str:
    """
    生成随机邮箱地址。

    邮箱前缀由本地随机生成，邮箱后缀从 `system_settings` 中的
    `chatgpt.registration_email_suffix` 读取。
    """
    if settings_repository is None:
        if db_pool is None:
            raise ValueError("错误：db_pool 或 settings_repository 至少需要传一个。")
        settings_repository = SystemSettingsRepository(db_pool)

    email_suffix = await settings_repository.get_chatgpt_registration_email_suffix()
    normalized_suffix = _normalize_email_suffix(email_suffix)
    prefix = generate_random_email_prefix(prefix_length)
    return f"{prefix}@{normalized_suffix}"


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
