"""防广告 / 防刷屏。"""
import logging
import re
import time
from collections import defaultdict, deque

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings
from bot.database import db
from bot.utils import fmt_duration, is_admin, mute_user, user_link

logger = logging.getLogger("antispam")
router = Router(name="antispam")

URL_RE = re.compile(r"(https?://|www\.|t\.me/|t\.lg\.me/)[^\s<>\"']+", re.IGNORECASE)

# 刷屏检测：{(chat_id): {user_id: deque[时间戳]}}
_flood: dict[int, dict[int, deque[float]]] = defaultdict(lambda: defaultdict(deque))


def _has_unwhitelisted_link(text: str) -> bool:
    for m in URL_RE.finditer(text):
        url = m.group(0).lower()
        host = re.sub(r"^https?://", "", url)
        host = re.sub(r"^www\.", "", host)
        host = host.split("/")[0].split("?")[0].split("#")[0].rstrip(".")
        if host not in settings.link_whitelist:
            return True
    return False


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def antispam_check(message: Message, bot: Bot) -> None:
    if message.from_user is None or message.from_user.is_bot:
        return
    chat_id = message.chat.id
    user_id = message.from_user.id

    if await is_admin(bot, chat_id, user_id):
        return

    if await db.get_config(chat_id, "antispam_enabled", "on") == "off":
        return

    # 1) 广告链接检测（非白名单域名）
    text = message.text or message.caption or ""
    if text and _has_unwhitelisted_link(text):
        try:
            await message.delete()
        except Exception:
            pass
        strikes = await db.incr_strike(chat_id, user_id)
        if strikes >= 3:
            await mute_user(bot, chat_id, user_id, 3600)
            await bot.send_message(
                chat_id,
                f"🚫 {user_link(user_id)} 多次发送广告链接，已被禁言 1 小时。",
            )
        else:
            await bot.send_message(
                chat_id,
                f"⚠️ {user_link(user_id)} 发送了疑似广告链接，消息已删除（累计 {strikes}/3）。",
            )
        return

    # 2) 刷屏检测（窗口内消息数超过阈值）
    now = time.time()
    q = _flood[chat_id][user_id]
    q.append(now)
    while q and now - q[0] > settings.flood_window:
        q.popleft()
    if len(q) >= settings.flood_threshold:
        q.clear()
        try:
            await message.delete()
        except Exception:
            pass
        await mute_user(bot, chat_id, user_id, settings.flood_mute_seconds)
        await bot.send_message(
            chat_id,
            f"🚫 {user_link(user_id)} 检测到刷屏，已被禁言 {fmt_duration(settings.flood_mute_seconds)}。",
        )


@router.message(Command("antispam"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_toggle_antispam(message: Message, bot: Bot) -> None:
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return
    arg = message.text.removeprefix("/antispam").strip().lower()
    if arg not in ("on", "off"):
        await message.answer("用法：<code>/antispam on|off</code>")
        return
    await db.set_config(message.chat.id, "antispam_enabled", arg)
    await message.answer(f"✅ 防广告/防刷屏已{'开启' if arg == 'on' else '关闭'}")


@router.message(Command("resetstrikes"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_reset_strikes(message: Message, bot: Bot) -> None:
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return
    target = message.reply_to_message
    if not target or target.from_user is None:
        await message.answer("请回复要重置违规计次的用户的消息")
        return
    await db.reset_strike(message.chat.id, target.from_user.id)
    await message.answer("✅ 违规计次已重置")
