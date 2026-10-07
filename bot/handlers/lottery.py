"""抽奖工具：管理员发起抽奖，成员点按钮参与，管理员点开奖随机抽取。"""
import random

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.database import db
from bot.utils import is_admin, user_link

router = Router(name="lottery")

MAX_WINNERS = 50


def lottery_markup(lottery_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎟 参与抽奖", callback_data=f"lj:{lottery_id}")],
            [InlineKeyboardButton(text="🎲 开奖（管理员）", callback_data=f"ld:{lottery_id}")],
        ]
    )


@router.message(Command("lottery"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_lottery(message: Message, bot: Bot) -> None:
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        await message.answer("⚠️ 只有群管理员才能发起抽奖。")
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("用法：<code>/lottery 人数 奖品</code>\n示例：<code>/lottery 3 现金红包 100 元</code>")
        return
    if not parts[1].isdigit():
        await message.answer("第 2 个参数请填中奖人数，例如 <code>/lottery 3 红包</code>")
        return
    count = int(parts[1])
    if count < 1 or count > MAX_WINNERS:
        await message.answer(f"中奖人数需在 1-{MAX_WINNERS} 之间")
        return
    prize = " ".join(parts[2:]).strip()
    if not prize:
        await message.answer("请填写奖品描述")
        return

    lottery_id = await db.create_lottery(message.chat.id, prize, count, message.from_user.id)
    await message.answer(
        f"🎉 <b>抽奖开始！</b>\n"
        f"🎁 奖品：{prize}\n"
        f"👥 中奖人数：{count} 人\n"
        f"👇 点下方按钮参与抽奖，管理员点开奖按钮抽取幸运儿",
        reply_markup=lottery_markup(lottery_id),
    )


@router.callback_query(F.data.startswith("lj:"))
async def lottery_join(callback: CallbackQuery) -> None:
    try:
        lottery_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("无效的抽奖", show_alert=True)
        return
    lottery = await db.get_lottery(lottery_id)
    if not lottery or lottery["status"] != "open":
        await callback.answer("抽奖已结束", show_alert=True)
        return
    ok = await db.join_lottery(
        lottery_id,
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.full_name or callback.from_user.first_name,
    )
    if ok:
        count = await db.lottery_entry_count(lottery_id)
        await callback.answer(f"✅ 已参与！当前共 {count} 人参与", show_alert=True)
    else:
        await callback.answer("你已经参与过啦", show_alert=True)


@router.callback_query(F.data.startswith("ld:"))
async def lottery_draw(callback: CallbackQuery, bot: Bot) -> None:
    try:
        lottery_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("无效的抽奖", show_alert=True)
        return
    if not await is_admin(bot, callback.message.chat.id, callback.from_user.id):
        await callback.answer("只有管理员可以开奖", show_alert=True)
        return
    lottery = await db.get_lottery(lottery_id)
    if not lottery or lottery["status"] != "open":
        await callback.answer("抽奖已结束", show_alert=True)
        return
    entries = await db.lottery_entries(lottery_id)
    if not entries:
        await callback.answer("还没有人参与抽奖", show_alert=True)
        return

    winners = random.sample(entries, min(lottery["winners_count"], len(entries)))
    await db.close_lottery(lottery_id)

    lines = [f"🎊 <b>开奖啦！</b>\n🎁 奖品：{lottery['prize']}"]
    for w in winners:
        name = w["name"] or w["username"] or str(w["user_id"])
        lines.append(f"🎉 {user_link(w['user_id'], name)}")
    await callback.message.answer("\n".join(lines))
    await callback.answer("🎲 已开奖")
