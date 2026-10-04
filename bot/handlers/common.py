"""入口命令 / 帮助。"""
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="common")

HELP_TEXT = (
    "🤖 <b>群管机器人命令手册</b>\n\n"
    "🛡 <b>入群与验证</b>\n"
    "/captcha on|off — 开关入群验证（管理员）\n"
    "/setwelcome 文案 — 设置欢迎语（管理员）\n"
    "/setfarewell 文案 — 设置欢送语（管理员）\n\n"
    "🚫 <b>管理员指令</b>（回复目标消息或 @用户名）\n"
    "/kick — 踢出（可重新加入）\n"
    "/ban — 封禁（不可加入）\n"
    "/unban — 解封\n"
    "/mute 5m — 禁言（支持 30s / 5m / 1h / 2d）\n"
    "/unmute — 解除禁言\n"
    "/del — 删除消息（回复目标消息）\n"
    "/pin — 置顶（回复目标消息）\n"
    "/unpin — 取消置顶（回复目标消息）\n\n"
    "🔤 <b>敏感词管理</b>（管理员）\n"
    "/addword 词 — 添加敏感词\n"
    "/delword 词 — 删除敏感词\n"
    "/listwords — 查看敏感词列表\n"
    "/resetstrikes — 重置违规计次（回复目标用户）\n\n"
    "📊 <b>统计</b>\n"
    "/stats — 今日发言排行 TOP10\n"
    "/mystats — 我的今日发言数\n\n"
    "💬 其他\n"
    "/help — 显示本帮助\n"
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "你好！我是群管机器人 🤖\n"
        "把我和 <b>群管理权限</b> 一起拉进群即可开始使用。\n\n" + HELP_TEXT
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
