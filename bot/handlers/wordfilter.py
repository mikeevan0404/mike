"""敏感词过滤：命中自动删除并计次，累计 3 次禁言 1 小时。"""
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.database import db
from bot.utils import is_admin, mute_user, user_link

router = Router(name="wordfilter")


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def word_check(message: Message, bot: Bot) -> None:
    if message.from_user is None or message.from_user.is_bot:
        return
    chat_id = message.chat.id
    user_id = message.from_user.id

    if await is_admin(bot, chat_id, user_id):
        return

    words = await db.get_words(chat_id)
    if not words:
        return

    text = (message.text or message.caption or "").lower()
    hit = next((w for w in words if w in text), None)
    if hit is None:
        return

    try:
        await message.delete()
    except Exception:
        pass
    strikes = await db.incr_strike(chat_id, user_id)
    if strikes >= 3:
        await mute_user(bot, chat_id, user_id, 3600)
        await bot.send_message(
            chat_id,
            f"🚫 {user_link(user_id)} 多次触发敏感词，已被禁言 1 小时。",
        )
    else:
        await bot.send_message(
            chat_id,
            f"⚠️ {user_link(user_id)} 的发言包含敏感词「{hit}」，已删除（累计 {strikes}/3）。",
        )


@router.message(Command("addword"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_add_word(message: Message, bot: Bot) -> None:
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return
    word = message.text.removeprefix("/addword").strip().lower()
    if not word or len(word) > 64:
        await message.answer("用法：<code>/addword 敏感词</code>")
        return
    await db.add_word(message.chat.id, word, message.from_user.id)
    await message.answer(f"✅ 已添加敏感词：{word}")


@router.message(Command("delword"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_del_word(message: Message, bot: Bot) -> None:
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return
    word = message.text.removeprefix("/delword").strip().lower()
    if not word:
        await message.answer("用法：<code>/delword 敏感词</code>")
        return
    ok = await db.del_word(message.chat.id, word)
    await message.answer(f"✅ 已删除敏感词：{word}" if ok else f"❌ 未找到敏感词：{word}")


@router.message(Command("listwords"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_list_words(message: Message, bot: Bot) -> None:
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return
    words = await db.get_words(message.chat.id)
    if not words:
        await message.answer("本群暂无敏感词")
        return
    text = "🔤 <b>本群敏感词列表</b>\n" + "\n".join(
        f"{i}. {w}" for i, w in enumerate(words, 1)
    )
    await message.answer(text)
