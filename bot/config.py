"""全局配置：从环境变量 / .env 文件加载。"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _int_list(raw: str) -> list[int]:
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def _str_list(raw: str) -> list[str]:
    return [x.strip().lower() for x in raw.split(",") if x.strip()]


@dataclass
class Settings:
    bot_token: str
    admin_ids: list[int]
    db_path: str
    link_whitelist: list[str]
    captcha_enabled: bool
    captcha_timeout: int
    flood_window: int
    flood_threshold: int
    flood_mute_seconds: int
    log_level: str
    proxy: str


def load_settings() -> Settings:
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        admin_ids=_int_list(os.getenv("ADMIN_IDS", "")),
        db_path=os.getenv("DB_PATH", "data/bot.db"),
        link_whitelist=_str_list(
            os.getenv(
                "LINK_WHITELIST",
                "t.me,telegram.me,telegram.dog,youtube.com,youtu.be,github.com,gist.github.com",
            )
        ),
        captcha_enabled=os.getenv("CAPTCHA_ENABLED", "true").strip().lower() == "true",
        captcha_timeout=int(os.getenv("CAPTCHA_TIMEOUT", "300")),
        flood_window=int(os.getenv("FLOOD_WINDOW", "10")),
        flood_threshold=int(os.getenv("FLOOD_THRESHOLD", "5")),
        flood_mute_seconds=int(os.getenv("FLOOD_MUTE_SECONDS", "600")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        proxy=os.getenv("PROXY", "").strip(),
    )


settings = load_settings()
