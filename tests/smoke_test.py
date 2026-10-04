"""冒烟测试：模块导入 + 数据库读写 + 工具函数（分步打印）。"""
import asyncio
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_T0 = time.time()


def step(name: str) -> None:
    print(f"[{time.time() - _T0:.1f}s] {name}", flush=True)


def main() -> None:
    # 1) 全部模块导入（验证 router 注册无循环依赖、无拼写错误）
    from bot.handlers import admin, antispam, captcha, common, stats, welcome, wordfilter
    from bot import main as bot_main  # noqa: F401

    routers = [
        common.router, welcome.router, captcha.router,
        antispam.router, wordfilter.router, stats.router, admin.router,
    ]
    step(f"[1] 模块导入 OK：{[r.name for r in routers]}")

    # 2) 数据库全功能冒烟测试（临时库）
    from bot.database import Database

    async def db_test() -> None:
        tmp = os.path.join(tempfile.mkdtemp(), "test.db")
        db = Database(tmp)
        await db.connect()
        step("[2a] connect OK")

        await db.set_config(-1001, "welcome_text", "你好 {name}")
        assert await db.get_config(-1001, "welcome_text") == "你好 {name}"
        step("[2b] config OK")

        await db.add_word(-1001, "广告", 1)
        await db.add_word(-1001, "广告", 1)  # 重复添加应忽略
        words = await db.get_words(-1001)
        assert words == ["广告"], words
        assert await db.del_word(-1001, "广告") is True
        assert await db.get_words(-1001) == []
        step("[2c] words OK")

        c1 = await db.incr_strike(-1001, 42)
        c2 = await db.incr_strike(-1001, 42)
        assert (c1, c2) == (1, 2), (c1, c2)
        await db.reset_strike(-1001, 42)
        assert await db.incr_strike(-1001, 42) == 1
        step("[2d] strikes OK")

        await db.incr_msg_count(-1001, 42, "alice", "Alice")
        await db.incr_msg_count(-1001, 42, "alice", "Alice")
        await db.incr_msg_count(-1001, 7, "bob", "Bob")
        top = await db.today_top(-1001, 10)
        assert len(top) == 2 and top[0]["msg_count"] == 2, [dict(r) for r in top]
        assert await db.user_today(-1001, 42) == 2
        assert await db.user_today(-1001, 999) == 0
        await db.close()
        step("[2] 数据库读写 OK：配置/敏感词/计次/统计 全部通过")

    asyncio.run(db_test())

    # 3) 工具函数
    from bot.utils import fmt_duration, parse_duration
    assert parse_duration("5m") == 300 and parse_duration("1h") == 3600 and parse_duration("2d") == 172800
    assert parse_duration("abc") is None
    assert fmt_duration(600) == "10 分钟"
    step("[3] 工具函数 OK：parse_duration / fmt_duration")
    step("ALL PASS")


if __name__ == "__main__":
    main()
