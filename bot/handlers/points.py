"""积分签到：每日签到、连续签到奖励、积分查询与排行榜。"""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings
from bot.database import db
from bot.utils import user_link

router = Router(name="points")


@router.message(Command("sign"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_sign(message: Message) -> None:
    if message.from_user is None or message.from_user.is_bot:
        return
    result = await db.sign_in(
        message.chat.id,
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name or message.from_user.first_name,
        daily=settings.sign_daily_points,
        streak_days=settings.sign_streak_days,
        streak_bonus=settings.sign_streak_bonus,
    )
    if not result["signed"]:
        await message.answer("⏰ 你今天已经签到过啦，明天再来～")
        return
    text = (
        f"✅ 签到成功！获得 <b>{result['gained']}</b> 积分"
        f"（连续签到 {result['streak']} 天）"
    )
    if result["bonus"]:
        text += f"\n🎉 连续签到 {settings.sign_streak_days} 天，额外奖励 +{settings.sign_streak_bonus}！"
    text += f"\n💰 当前积分：<b>{result['points']}</b>"
    await message.answer(text)


@router.message(Command("points"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_points(message: Message) -> None:
    info = await db.get_points(message.chat.id, message.from_user.id)
    await message.answer(f"💰 你的积分：<b>{info['points']}</b>（连续签到 {info['streak']} 天）")


@router.message(Command("top"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_top(message: Message) -> None:
    rows = await db.top_points(message.chat.id, 10)
    if not rows:
        await message.answer("还没有人获得积分，发 /sign 签到吧～")
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 <b>积分排行榜 TOP10</b>"]
    for i, row in enumerate(rows, 1):
        name = row["name"] or row["username"] or str(row["user_id"])
        prefix = medals[i - 1] if i <= 3 else f"{i}."
        lines.append(f"{prefix} {user_link(row['user_id'], name)} —— {row['points']} 分")
    await message.answer("\n".join(lines))
