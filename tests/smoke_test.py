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
    from bot import main as bot_main  # noqa: F401

    routers = [
        common.router, welcome.router, captcha.router,
        antispam.router, wordfilter.router, keyword.router,
        points.router, lottery.router, ai_reply.router,
        stats.router, admin.router,
    ]
    step(f"[1] 模块导入 OK：{len(routers)} 个 router：{[r.name for r in routers]}")

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
        step("[2e] msg_stats OK")

        # 积分签到：首次签到 / 当日重复签到 / 积分与排行
        s1 = await db.sign_in(-1001, 42, "alice", "Alice")
        assert s1["signed"] and s1["streak"] == 1 and s1["points"] == 1, s1
        s2 = await db.sign_in(-1001, 42, "alice", "Alice")  # 当日重复
        assert not s2["signed"], s2
        await db.sign_in(-1001, 7, "bob", "Bob")
        top_pts = await db.top_points(-1001, 5)
        # 两名用户各 1 分，排序不依赖顺序，只校验成员与分值
        assert len(top_pts) == 2 and all(r["points"] == 1 for r in top_pts), [dict(r) for r in top_pts]
        assert {r["user_id"] for r in top_pts} == {42, 7}
        step("[2f] points 积分签到 OK")

        # 抽奖：创建 / 参与 / 去重 / 开奖数据
        lid = await db.create_lottery(-1001, "现金红包 100 元", 2, 42)
        assert await db.join_lottery(lid, 1, "u1", "U1") is True
        assert await db.join_lottery(lid, 1, "u1", "U1") is False  # 重复参与
        assert await db.join_lottery(lid, 2, "u2", "U2") is True
        assert await db.lottery_entry_count(lid) == 2
        row = await db.get_lottery(lid)
        assert row and row["status"] == "open" and row["winners_count"] == 2, dict(row)
        entries = await db.lottery_entries(lid)
        assert len(entries) == 2
        await db.close_lottery(lid)
        assert (await db.get_lottery(lid))["status"] == "closed"
        step("[2g] lottery 抽奖 OK")

        # 关键词回复：增删查与命中
        await db.add_keyword(-1001, "群规", "进群请先看置顶群规", 42)
        await db.add_keyword(-1001, "价格", "套餐价格请私聊管理", 42)
        assert await db.find_keyword(-1001, "请问群规是什么") == "进群请先看置顶群规"
        assert await db.find_keyword(-1001, "今天天气不错") is None
        assert await db.del_keyword(-1001, "价格") is True
        assert await db.del_keyword(-1001, "价格") is False
        rows = await db.get_keywords(-1001)
        assert len(rows) == 1 and rows[0]["keyword"] == "群规", [dict(r) for r in rows]
        step("[2h] keyword 关键词面板 OK")

        await db.close()
        step("[2] 数据库读写 OK：全部 8 组数据通过")

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
