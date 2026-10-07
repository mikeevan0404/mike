"""SQLite 数据存储（aiosqlite，无需外部数据库）。"""
import os
from datetime import datetime, timedelta

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
            CREATE TABLE IF NOT EXISTS user_points(
                chat_id        INTEGER NOT NULL,
                user_id        INTEGER NOT NULL,
                username       TEXT,
                name           TEXT,
                points         INTEGER NOT NULL DEFAULT 0,
                streak         INTEGER NOT NULL DEFAULT 0,
                last_sign_date TEXT,
                PRIMARY KEY(chat_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS lotteries(
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id       INTEGER NOT NULL,
                prize         TEXT NOT NULL,
                winners_count INTEGER NOT NULL DEFAULT 1,
                creator_id    INTEGER NOT NULL,
                status        TEXT NOT NULL DEFAULT 'open',
                created_at    TEXT
            );
            CREATE TABLE IF NOT EXISTS lottery_entries(
                lottery_id INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                username   TEXT,
                name       TEXT,
                PRIMARY KEY(lottery_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS keyword_replies(
                chat_id    INTEGER NOT NULL,
                keyword    TEXT NOT NULL,
                reply      TEXT NOT NULL,
                created_by INTEGER,
                PRIMARY KEY(chat_id, keyword)
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

    # ---------- 积分签到 ----------
    async def get_points(self, chat_id: int, user_id: int) -> dict:
        cur = await self.conn.execute(
            "SELECT points, streak, last_sign_date FROM user_points "
            "WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )
        row = await cur.fetchone()
        await cur.close()
        if row:
            return {"points": row["points"], "streak": row["streak"], "last_sign_date": row["last_sign_date"]}
        return {"points": 0, "streak": 0, "last_sign_date": None}

    async def sign_in(
        self,
        chat_id: int,
        user_id: int,
        username: str | None,
        name: str,
        daily: int = 1,
        streak_days: int = 7,
        streak_bonus: int = 3,
    ) -> dict:
        """每日签到。今天已签到返回 signed=False，否则累加积分并返回结果。"""
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        info = await self.get_points(chat_id, user_id)
        if info["last_sign_date"] == today:
            return {"signed": False, "gained": 0, "streak": info["streak"], "points": info["points"], "bonus": False}

        streak = info["streak"] + 1 if info["last_sign_date"] == yesterday else 1
        bonus = streak_bonus if (streak >= streak_days and streak % streak_days == 0) else 0
        gained = daily + bonus
        new_points = info["points"] + gained

        await self.conn.execute(
            "INSERT INTO user_points(chat_id, user_id, username, name, points, streak, last_sign_date) "
            "VALUES(?,?,?,?,?,?,?) "
            "ON CONFLICT(chat_id, user_id) DO UPDATE SET "
            "username=excluded.username, name=excluded.name, points=excluded.points, "
            "streak=excluded.streak, last_sign_date=excluded.last_sign_date",
            (chat_id, user_id, username, name, new_points, streak, today),
        )
        await self.conn.commit()
        return {"signed": True, "gained": gained, "streak": streak, "points": new_points, "bonus": bonus > 0}

    async def top_points(self, chat_id: int, limit: int = 10) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT user_id, username, name, points, streak FROM user_points "
            "WHERE chat_id=? ORDER BY points DESC LIMIT ?",
            (chat_id, limit),
        )
        rows = await cur.fetchall()
        await cur.close()
        return rows

    # ---------- 抽奖 ----------
    async def create_lottery(self, chat_id: int, prize: str, winners_count: int, creator_id: int) -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = await self.conn.execute(
            "INSERT INTO lotteries(chat_id, prize, winners_count, creator_id, status, created_at) "
            "VALUES(?,?,?,?,'open',?)",
            (chat_id, prize, winners_count, creator_id, now),
        )
        await self.conn.commit()
        return cur.lastrowid

    async def get_lottery(self, lottery_id: int) -> aiosqlite.Row | None:
        cur = await self.conn.execute("SELECT * FROM lotteries WHERE id=?", (lottery_id,))
        row = await cur.fetchone()
        await cur.close()
        return row

    async def join_lottery(self, lottery_id: int, user_id: int, username: str | None, name: str) -> bool:
        """参与抽奖；返回 True=成功加入，False=重复参与。"""
        cur = await self.conn.execute(
            "INSERT OR IGNORE INTO lottery_entries(lottery_id, user_id, username, name) VALUES(?,?,?,?)",
            (lottery_id, user_id, username, name),
        )
        await self.conn.commit()
        return cur.rowcount > 0

    async def lottery_entry_count(self, lottery_id: int) -> int:
        cur = await self.conn.execute(
            "SELECT COUNT(*) AS c FROM lottery_entries WHERE lottery_id=?", (lottery_id,)
        )
        row = await cur.fetchone()
        await cur.close()
        return row["c"]

    async def lottery_entries(self, lottery_id: int) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT user_id, username, name FROM lottery_entries WHERE lottery_id=?", (lottery_id,)
        )
        rows = await cur.fetchall()
        await cur.close()
        return rows

    async def close_lottery(self, lottery_id: int) -> None:
        await self.conn.execute(
            "UPDATE lotteries SET status='closed' WHERE id=?", (lottery_id,)
        )
        await self.conn.commit()

    # ---------- 关键词自动回复 ----------
    async def add_keyword(self, chat_id: int, keyword: str, reply: str, created_by: int) -> None:
        await self.conn.execute(
            "INSERT OR REPLACE INTO keyword_replies(chat_id, keyword, reply, created_by) VALUES(?,?,?,?)",
            (chat_id, keyword, reply, created_by),
        )
        await self.conn.commit()

    async def del_keyword(self, chat_id: int, keyword: str) -> bool:
        cur = await self.conn.execute(
            "DELETE FROM keyword_replies WHERE chat_id=? AND keyword=?", (chat_id, keyword)
        )
        await self.conn.commit()
        return cur.rowcount > 0

    async def get_keywords(self, chat_id: int) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT keyword, reply FROM keyword_replies WHERE chat_id=? ORDER BY rowid", (chat_id,)
        )
        rows = await cur.fetchall()
        await cur.close()
        return rows

    async def find_keyword(self, chat_id: int, text: str) -> str | None:
        """文本包含关键词即命中，返回对应回复内容。"""
        lower = text.lower()
        for row in await self.get_keywords(chat_id):
            if row["keyword"].lower() in lower:
                return row["reply"]
        return None


# 全局单例
db = Database(settings.db_path)
