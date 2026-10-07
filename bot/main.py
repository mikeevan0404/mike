"""Telegram 群管机器人入口。"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.database import db
from bot.handlers import (
    admin,
    ai_reply,
    antispam,
    captcha,
    common,
    keyword,
    lottery,
    points,
    stats,
    welcome,
    wordfilter,
)

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bot")


async def main() -> None:
    if not settings.bot_token:
        logger.error("未配置 BOT_TOKEN，请在 .env 中填写 @BotFather 获取的 token 后重试。")
        raise SystemExit(1)

    await db.connect()
    logger.info("数据库已就绪：%s", settings.db_path)

    # 国内服务器可通过 PROXY 配置代理访问 Telegram API（海外服务器留空即可）
    session = AiohttpSession(proxy=settings.proxy) if settings.proxy else None
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_routers(
        common.router,
        welcome.router,
        captcha.router,
        antispam.router,
        wordfilter.router,
        keyword.router,
        points.router,
        lottery.router,
        ai_reply.router,
        stats.router,
        admin.router,
    )

    me = await bot.get_me()
    logger.info("机器人 @%s 已启动，开始轮询更新…", me.username)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        try:
            asyncio.run(db.close())
        except Exception:
            pass
