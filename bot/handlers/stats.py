"""群活跃统计：按自然日统计发言数。"""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.database import db
from bot.utils import user_link

router = Router(name="stats")

_SKIP_COMMANDS = {"start", "help", "stats", "mystats"}


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def count_message(message: Message) -> None:
    if message.from_user is None or message.from_user.is_bot:
        return
    if message.text and message.text.lstrip("/").split()[0].lower() in _SKIP_COMMANDS:
        return
    await db.incr_msg_count(
        message.chat.id,
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name or message.from_user.first_name,
    )


@router.message(Command("stats"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_stats(message: Message) -> None:
    rows = await db.today_top(message.chat.id, 10)
    if not rows:
        await message.answer("📊 今天还没有人发言～")
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = ["📊 <b>今日发言排行 TOP10</b>"]
    for i, row in enumerate(rows, 1):
        name = row["name"] or row["username"] or str(row["user_id"])
        prefix = medals[i - 1] if i <= 3 else f"{i}."
        lines.append(f"{prefix} {user_link(row['user_id'], name)} —— {row['msg_count']} 条")
    await message.answer("\n".join(lines))


@router.message(Command("mystats"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_my_stats(message: Message) -> None:
    cnt = await db.user_today(message.chat.id, message.from_user.id)
    await message.answer(f"📈 你今天在群里发言了 <b>{cnt}</b> 条。")
