"""SQLite 数据存储（aiosqlite，无需外部数据库）。"""
import os
from datetime import datetime

import aiosqlite

from bot.config import settings


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS group_config(
                chat_id INTEGER NOT NULL,
                key      TEXT NOT NULL,
                value    TEXT,
                PRIMARY KEY(chat_id, key)
            );
            CREATE TABLE IF NOT EXISTS banned_words(
                chat_id    INTEGER NOT NULL,
                word       TEXT NOT NULL,
                created_by INTEGER,
                PRIMARY KEY(chat_id, word)
            );
            CREATE TABLE IF NOT EXISTS strikes(
                chat_id    INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                count      INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT,
                PRIMARY KEY(chat_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS msg_stats(
                chat_id   INTEGER NOT NULL,
                user_id   INTEGER NOT NULL,
                username  TEXT,
                name      TEXT,
                msg_count INTEGER NOT NULL DEFAULT 0,
                stat_date TEXT NOT NULL,
                PRIMARY KEY(chat_id, user_id, stat_date)
            );
            """
        )
        await self.conn.commit()

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()
            self.conn = None

    # ---------- 群配置 ----------
    async def get_config(self, chat_id: int, key: str, default: str | None = None) -> str | None:
        cur = await self.conn.execute(
            "SELECT value FROM group_config WHERE chat_id=? AND key=?", (chat_id, key)
        )
        row = await cur.fetchone()
        await cur.close()
        return row["value"] if row else default

    async def set_config(self, chat_id: int, key: str, value: str) -> None:
        await self.conn.execute(
            "INSERT INTO group_config(chat_id, key, value) VALUES(?,?,?) "
            "ON CONFLICT(chat_id, key) DO UPDATE SET value=excluded.value",
            (chat_id, key, value),
        )
        await self.conn.commit()

    # ---------- 敏感词 ----------
    async def get_words(self, chat_id: int) -> list[str]:
        cur = await self.conn.execute(
            "SELECT word FROM banned_words WHERE chat_id=? ORDER BY rowid", (chat_id,)
        )
        rows = await cur.fetchall()
        await cur.close()
        return [r["word"] for r in rows]

    async def add_word(self, chat_id: int, word: str, created_by: int) -> None:
        await self.conn.execute(
            "INSERT OR IGNORE INTO banned_words(chat_id, word, created_by) VALUES(?,?,?)",
            (chat_id, word, created_by),
        )
        await self.conn.commit()

    async def del_word(self, chat_id: int, word: str) -> bool:
        cur = await self.conn.execute(
            "DELETE FROM banned_words WHERE chat_id=? AND word=?", (chat_id, word)
        )
        await self.conn.commit()
        return cur.rowcount > 0

    # ---------- 违规计次（24 小时内累计，超过 24h 重置） ----------
    async def incr_strike(self, chat_id: int, user_id: int) -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 24 小时内累计 +1；距上次违规超过 24 小时则重置为 1
        await self.conn.execute(
            "INSERT INTO strikes(chat_id, user_id, count, updated_at) VALUES(?,?,1,?) "
            "ON CONFLICT(chat_id, user_id) DO UPDATE SET "
            "count = CASE WHEN datetime(updated_at, '+1 day') > ? THEN count + 1 ELSE 1 END, "
            "updated_at = excluded.updated_at",
            (chat_id, user_id, now, now),
        )
        await self.conn.commit()
        cur = await self.conn.execute(
            "SELECT count FROM strikes WHERE chat_id=? AND user_id=?", (chat_id, user_id)
        )
        row = await cur.fetchone()
        await cur.close()
        return row["count"] if row else 1

    async def reset_strike(self, chat_id: int, user_id: int) -> None:
        await self.conn.execute(
            "DELETE FROM strikes WHERE chat_id=? AND user_id=?", (chat_id, user_id)
        )
        await self.conn.commit()

    # ---------- 发言统计 ----------
    async def incr_msg_count(self, chat_id: int, user_id: int, username: str | None, name: str) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        await self.conn.execute(
            "INSERT INTO msg_stats(chat_id, user_id, username, name, msg_count, stat_date) "
            "VALUES(?,?,?,?,1,?) "
            "ON CONFLICT(chat_id, user_id, stat_date) DO UPDATE SET "
            "msg_count = msg_count + 1, username = excluded.username, name = excluded.name",
            (chat_id, user_id, username, name, today),
        )
        await self.conn.commit()

    async def today_top(self, chat_id: int, limit: int = 10) -> list[aiosqlite.Row]:
        today = datetime.now().strftime("%Y-%m-%d")
        cur = await self.conn.execute(
            "SELECT user_id, username, name, msg_count FROM msg_stats "
            "WHERE chat_id=? AND stat_date=? ORDER BY msg_count DESC LIMIT ?",
            (chat_id, today, limit),
        )
        rows = await cur.fetchall()
        await cur.close()
        return rows

    async def user_today(self, chat_id: int, user_id: int) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        cur = await self.conn.execute(
            "SELECT msg_count FROM msg_stats WHERE chat_id=? AND user_id=? AND stat_date=?",
            (chat_id, user_id, today),
        )
        row = await cur.fetchone()
        await cur.close()
        return row["msg_count"] if row else 0


# 全局单例
db = Database(settings.db_path)
