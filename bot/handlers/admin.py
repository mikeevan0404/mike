"""管理员指令：踢人 / 封禁 / 禁言 / 置顶 / 删除消息等。"""
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message

from bot.utils import (
    ban_user,
    fmt_duration,
    is_admin,
    kick_user,
    mute_user,
    parse_duration,
    unban_user,
    unmute_user,
    user_link,
)

router = Router(name="admin")


async def _try_action(action, *args, **kwargs) -> tuple[bool, str]:
    """执行管理动作，返回 (是否成功, 提示信息)。"""
    try:
        await action(*args, **kwargs)
        return True, ""
    except TelegramBadRequest as exc:
        return False, (
            f"❌ 操作失败：{exc.text or exc.message}。"
            "请确认机器人是群管理员并拥有对应权限。"
        )


async def _require_admin(message: Message, bot: Bot) -> bool:
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        await message.answer("⚠️ 只有群管理员才能使用此指令。")
        return False
    return True


async def _resolve_target(message: Message) -> tuple[int | None, str | None]:
    """从回复消息或 @用户名 / 数字 ID 解析目标用户。"""
    if message.reply_to_message and message.reply_to_message.from_user:
        u = message.reply_to_message.from_user
        return u.id, u.full_name or u.first_name
    parts = message.text.split()
    if len(parts) >= 2:
        arg = parts[1].strip()
        if arg.startswith("@"):
            try:
                member = await message.bot.get_chat_member(message.chat.id, arg)
                return member.user.id, member.user.full_name or member.user.first_name
            except TelegramBadRequest:
                return None, None
        if arg.lstrip("-").isdigit():
            return int(arg), arg
    return None, None


def _duration_from_args(args: list[str]) -> int | None:
    for a in args[1:]:
        dur = parse_duration(a)
        if dur is not None:
            return dur
    return None


async def _check_target_not_admin(message: Message, bot: Bot, user_id: int) -> bool:
    if await is_admin(bot, message.chat.id, user_id):
        await message.answer("⚠️ 不能对管理员/群主执行此操作。")
        return False
    return True


@router.message(Command("kick"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_kick(message: Message, bot: Bot) -> None:
    if not await _require_admin(message, bot):
        return
    user_id, name = await _resolve_target(message)
    if user_id is None:
        await message.answer("用法：<code>/kick</code>（回复要踢出的用户，或 /kick @用户名）")
        return
    if not await _check_target_not_admin(message, bot, user_id):
        return
    ok, err = await _try_action(kick_user, bot, message.chat.id, user_id)
    await message.answer(f"👢 已踢出 {user_link(user_id, name)}" if ok else err)


@router.message(Command("ban"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_ban(message: Message, bot: Bot) -> None:
    if not await _require_admin(message, bot):
        return
    user_id, name = await _resolve_target(message)
    if user_id is None:
        await message.answer("用法：<code>/ban</code>（回复要封禁的用户，或 /ban @用户名）")
        return
    if not await _check_target_not_admin(message, bot, user_id):
        return
    ok, err = await _try_action(ban_user, bot, message.chat.id, user_id)
    await message.answer(f"⛔ 已封禁 {user_link(user_id, name)}" if ok else err)


@router.message(Command("unban"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_unban(message: Message, bot: Bot) -> None:
    if not await _require_admin(message, bot):
        return
    user_id, name = await _resolve_target(message)
    if user_id is None:
        await message.answer("用法：<code>/unban</code>（回复用户，或 /unban @用户名）")
        return
    ok, err = await _try_action(unban_user, bot, message.chat.id, user_id)
    await message.answer(f"✅ 已解封 {user_link(user_id, name)}" if ok else err)


@router.message(Command("mute"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_mute(message: Message, bot: Bot) -> None:
    if not await _require_admin(message, bot):
        return
    user_id, name = await _resolve_target(message)
    if user_id is None:
        await message.answer("用法：<code>/mute 5m</code>（回复用户，或 /mute @用户名 1h）")
        return
    if not await _check_target_not_admin(message, bot, user_id):
        return
    dur = _duration_from_args(message.text.split())
    if dur is None:
        await message.answer("请指定禁言时长，例如 <code>/mute 5m</code>（支持 30s / 5m / 1h / 2d）")
        return
    ok, err = await _try_action(mute_user, bot, message.chat.id, user_id, dur)
    await message.answer(
        f"🔇 已禁言 {user_link(user_id, name)} {fmt_duration(dur)}" if ok else err
    )


@router.message(Command("unmute"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_unmute(message: Message, bot: Bot) -> None:
    if not await _require_admin(message, bot):
        return
    user_id, name = await _resolve_target(message)
    if user_id is None:
        await message.answer("用法：<code>/unmute</code>（回复用户，或 /unmute @用户名）")
        return
    ok, err = await _try_action(unmute_user, bot, message.chat.id, user_id)
    await message.answer(f"🔊 已解除禁言 {user_link(user_id, name)}" if ok else err)


@router.message(Command("del"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_del(message: Message, bot: Bot) -> None:
    if not await _require_admin(message, bot):
        return
    if not message.reply_to_message:
        await message.answer("请回复要删除的消息")
        return
    ok, err = await _try_action(message.reply_to_message.delete)
    await message.answer("🗑 已删除" if ok else err)


@router.message(Command("pin"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_pin(message: Message, bot: Bot) -> None:
    if not await _require_admin(message, bot):
        return
    if not message.reply_to_message:
        await message.answer("请回复要置顶的消息")
        return
    ok, err = await _try_action(message.reply_to_message.pin, disable_notification=True)
    await message.answer("📌 已置顶" if ok else err)


@router.message(Command("unpin"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_unpin(message: Message, bot: Bot) -> None:
    if not await _require_admin(message, bot):
        return
    if not message.reply_to_message:
        await message.answer("请回复要取消置顶的消息")
        return
    ok, err = await _try_action(message.reply_to_message.unpin)
    await message.answer("📌 已取消置顶" if ok else err)
