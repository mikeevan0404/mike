"""入群验证码：新人入群需点击按钮验证，超时未验证自动移出群聊。"""
import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.config import settings
from bot.database import db
from bot.handlers.welcome import DEFAULT_WELCOME, member_name
from bot.utils import is_admin, render_template, user_link

logger = logging.getLogger("captcha")
router = Router(name="captcha")

# 待验证任务表：{(chat_id, user_id): asyncio.Task}
_pending: dict[tuple[int, int], asyncio.Task] = {}


def _key(chat_id: int, user_id: int) -> tuple[int, int]:
    return (chat_id, user_id)


async def start_captcha(event: ChatMemberUpdated, bot: Bot) -> None:
    chat_id = event.chat.id
    user = event.new_chat_member.user
    key = _key(chat_id, user.id)

    # 用户重复加入时，取消上一个未完成的验证任务
    old_task = _pending.pop(key, None)
    if old_task:
        old_task.cancel()

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ 我是真人，验证通过",
                    callback_data=f"captcha:{chat_id}:{user.id}",
                )
            ]
        ]
    )
    msg = await bot.send_message(
        chat_id,
        f"👋 欢迎 <b>{member_name(user)}</b> 加入本群！\n"
        f"本群开启了入群验证，请点击下方按钮完成验证。\n"
        f"⏳ <b>{settings.captcha_timeout} 秒</b>内未验证将被移出群聊。",
        reply_markup=markup,
    )
    _pending[key] = asyncio.create_task(
        _timeout_kick(bot, chat_id, user.id, msg.message_id)
    )


async def _timeout_kick(bot: Bot, chat_id: int, user_id: int, message_id: int) -> None:
    await asyncio.sleep(settings.captcha_timeout)
    key = _key(chat_id, user_id)
    if key not in _pending:
        return  # 已通过验证
    _pending.pop(key, None)
    try:
        await bot.ban_chat_member(chat_id, user_id)
        await bot.unban_chat_member(chat_id, user_id)
    except Exception as exc:
        logger.warning("验证超时移出用户失败: %s", exc)
        return
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass
    await bot.send_message(
        chat_id,
        f"⚠️ {user_link(user_id, '未通过验证的用户')} 超时未验证，已被移出群聊。",
    )


@router.callback_query(F.data.startswith("captcha:"))
async def on_captcha_pass(callback: CallbackQuery, bot: Bot) -> None:
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("无效的验证请求")
        return
    try:
        chat_id, user_id = int(parts[1]), int(parts[2])
    except ValueError:
        await callback.answer("无效的验证请求")
        return

    if callback.from_user.id != user_id:
        await callback.answer("这不是你的验证按钮哦", show_alert=True)
        return

    key = _key(chat_id, user_id)
    task = _pending.pop(key, None)
    if task is None:
        await callback.answer("验证已过期", show_alert=True)
        return
    task.cancel()

    try:
        await callback.message.delete()
    except Exception:
        pass

    # 通过验证，发送欢迎语
    template = (await db.get_config(chat_id, "welcome_text")) or DEFAULT_WELCOME
    count = 0
    try:
        count = await bot.get_chat_member_count(chat_id)
    except Exception:
        pass
    text = render_template(
        template,
        name=callback.from_user.full_name or callback.from_user.first_name,
        username=callback.from_user.username,
        count=count,
    )
    await bot.send_message(chat_id, text)

    await callback.answer("✅ 验证通过，欢迎加入！", show_alert=True)


@router.message(Command("captcha"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_toggle_captcha(message: Message, bot: Bot) -> None:
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return
    arg = message.text.removeprefix("/captcha").strip().lower()
    if arg not in ("on", "off"):
        await message.answer("用法：<code>/captcha on|off</code>")
        return
    await db.set_config(message.chat.id, "captcha_enabled", arg)
    await message.answer(f"✅ 入群验证已{'开启' if arg == 'on' else '关闭'}")
