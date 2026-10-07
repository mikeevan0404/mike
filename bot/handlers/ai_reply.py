"""AI 自动回复：群聊 @机器人 或回复它时触发，私聊直接对话。

使用 OpenAI 兼容接口（支持国内中转 base_url），需配置 AI_ENABLED=true 与 AI_API_KEY。
"""
import logging
import time

import aiohttp
from aiogram import Bot, F, Router
from aiogram.types import Message

from bot.config import settings

logger = logging.getLogger("ai_reply")
router = Router(name="ai_reply")

# 限流：{user_id: 上次调用时间戳}
_last_call: dict[int, float] = {}

MAX_REPLY_LEN = 4000


async def ask_ai(user_text: str) -> str:
    url = f"{settings.ai_base_url}/chat/completions"
    payload = {
        "model": settings.ai_model,
        "messages": [
            {"role": "system", "content": settings.ai_system_prompt},
            {"role": "user", "content": user_text},
        ],
        "max_tokens": 500,
        "temperature": 0.7,
    }
    headers = {
        "Authorization": f"Bearer {settings.ai_api_key}",
        "Content-Type": "application/json",
    }
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            data = await resp.json(content_type=None)
            if resp.status != 200:
                raise RuntimeError(f"AI API 返回 {resp.status}: {data}")
            return data["choices"][0]["message"]["content"].strip()


def _group_question(message: Message, bot_username: str | None) -> str | None:
    """群聊中提取提问：回复了机器人，或消息里 @了机器人。"""
    text = message.text or ""
    if message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.id == message.bot.id:
            return text.strip()
    if bot_username and f"@{bot_username}".lower() in text.lower():
        return text.lower().replace(f"@{bot_username}".lower(), "", 1).strip() or text.strip()
    return None


@router.message(F.text)
async def ai_reply(message: Message, bot: Bot) -> None:
    if not settings.ai_enabled or not settings.ai_api_key:
        return
    if message.from_user is None or message.from_user.is_bot:
        return

    if message.chat.type == "private":
        question = (message.text or "").strip()
    else:
        bot_username = bot.me.username if bot.me else None
        question = _group_question(message, bot_username)
        if question is None:
            return

    if not question:
        await message.answer("🤖 你想问什么？直接说出你的问题即可。")
        return

    # 限流：同一用户间隔内只回复一次
    now = time.time()
    if now - _last_call.get(message.from_user.id, 0) < settings.ai_min_interval:
        return
    _last_call[message.from_user.id] = now

    try:
        answer = await ask_ai(question)
    except Exception as exc:
        logger.warning("AI 调用失败: %s", exc)
        await message.answer("🤖 AI 暂时不可用，请稍后再试。")
        return

    if len(answer) > MAX_REPLY_LEN:
        answer = answer[:MAX_REPLY_LEN] + "…"
    await message.answer(answer)
