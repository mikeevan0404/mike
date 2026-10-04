"""欢迎 / 欢送新成员。"""
from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.filters import Command
from aiogram.types import ChatMemberUpdated, Message

from bot.database import db
from bot.utils import is_admin, render_template

router = Router(name="welcome")

DEFAULT_WELCOME = "欢迎 <b>{name}</b> 加入本群！🎉 记得查看群规，友好发言～（当前共 {count} 位成员）"
DEFAULT_FAREWELL = "{name} 离开了本群。"


def member_name(user) -> str:
    return user.full_name or user.first_name or "新成员"


async def _member_count(bot: Bot, chat_id: int) -> int:
    try:
        return await bot.get_chat_member_count(chat_id)
    except Exception:
        return 0


@router.chat_member(F.new_chat_member.status == ChatMemberStatus.MEMBER)
async def on_member_join(event: ChatMemberUpdated, bot: Bot) -> None:
    if event.new_chat_member.user.id == bot.id:
        return  # 忽略机器人自己被拉进群
    user = event.new_chat_member.user
    captcha_enabled = await db.get_config(event.chat.id, "captcha_enabled", "on")
    if captcha_enabled != "off":
        from bot.handlers.captcha import start_captcha  # 延迟导入，避免循环依赖

        await start_captcha(event, bot)
        return
    await send_welcome(bot, event.chat.id, user)


async def send_welcome(bot: Bot, chat_id: int, user) -> None:
    template = (await db.get_config(chat_id, "welcome_text")) or DEFAULT_WELCOME
    count = await _member_count(bot, chat_id)
    text = render_template(template, name=member_name(user), username=user.username, count=count)
    await bot.send_message(chat_id, text)


@router.chat_member(
    F.old_chat_member.status == ChatMemberStatus.MEMBER,
    F.new_chat_member.status == ChatMemberStatus.LEFT,
)
async def on_member_left(event: ChatMemberUpdated, bot: Bot) -> None:
    if event.old_chat_member.user.id == bot.id:
        return
    user = event.old_chat_member.user
    template = (await db.get_config(event.chat.id, "farewell_text")) or DEFAULT_FAREWELL
    text = render_template(template, name=member_name(user), username=user.username, count=0)
    await bot.send_message(event.chat.id, text)


@router.message(Command("setwelcome"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_set_welcome(message: Message, bot: Bot) -> None:
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return
    text = message.text.removeprefix("/setwelcome").strip()
    if not text:
        await message.answer("用法：<code>/setwelcome 欢迎语</code>\n支持占位符：{name} {username} {count}")
        return
    await db.set_config(message.chat.id, "welcome_text", text)
    await message.answer("✅ 欢迎语已更新")


@router.message(Command("setfarewell"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_set_farewell(message: Message, bot: Bot) -> None:
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return
    text = message.text.removeprefix("/setfarewell").strip()
    if not text:
        await message.answer("用法：<code>/setfarewell 欢送语</code>\n支持占位符：{name} {username}")
        return
    await db.set_config(message.chat.id, "farewell_text", text)
    await message.answer("✅ 欢送语已更新")
