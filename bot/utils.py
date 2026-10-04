"""公共工具：权限判断、管理动作、格式化。"""
import re
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatPermissions

from bot.config import settings

DURATION_RE = re.compile(r"^(\d+)\s*([smhd])$")
_DUR_UNIT = {"s": 1, "m": 60, "h": 3600, "d": 86400}


async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """判断用户是否为群主 / 管理员 / 超级管理员。"""
    if user_id in settings.admin_ids:
        return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR)
    except Exception:
        return False


async def kick_user(bot: Bot, chat_id: int, user_id: int) -> None:
    """踢出（可重新加入）。"""
    await bot.ban_chat_member(chat_id, user_id)
    await bot.unban_chat_member(chat_id, user_id)


async def ban_user(bot: Bot, chat_id: int, user_id: int) -> None:
    await bot.ban_chat_member(chat_id, user_id)


async def unban_user(bot: Bot, chat_id: int, user_id: int) -> None:
    await bot.unban_chat_member(chat_id, user_id)


async def mute_user(bot: Bot, chat_id: int, user_id: int, seconds: int) -> None:
    until = int(datetime.now(timezone.utc).timestamp()) + seconds
    await bot.restrict_chat_member(
        chat_id,
        user_id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until,
    )


async def unmute_user(bot: Bot, chat_id: int, user_id: int) -> None:
    chat = await bot.get_chat(chat_id)
    perms = chat.permissions or ChatPermissions(can_send_messages=True)
    await bot.restrict_chat_member(chat_id, user_id, permissions=perms)


def parse_duration(arg: str) -> int | None:
    """把 '30s' '5m' '1h' '2d' 解析为秒数，解析失败返回 None。"""
    m = DURATION_RE.match(arg.strip().lower())
    if not m:
        return None
    return int(m.group(1)) * _DUR_UNIT[m.group(2)]


def fmt_duration(secs: int) -> str:
    if secs % 3600 == 0:
        return f"{secs // 3600} 小时"
    if secs % 60 == 0:
        return f"{secs // 60} 分钟"
    return f"{secs} 秒"


def render_template(template: str, name: str, username: str | None, count: int) -> str:
    return (
        template.replace("{name}", name)
        .replace("{username}", username or "")
        .replace("{count}", str(count))
    )


def user_link(user_id: int, name: str | None = None) -> str:
    return f'<a href="tg://user?id={user_id}">{name or "该用户"}</a>'
