#!/usr/bin/env python3
"""Telegram 连通性验证脚本（供 GitHub Actions 使用）。

- 读取环境变量 BOT_TOKEN（必填，来自 GitHub Secrets）
- 读取环境变量 ADMIN_IDS（可选，逗号分隔的数字 ID）
- 用 aiogram 调用 getMe 验证 token 有效
- 若配置了 ADMIN_IDS，向第一位管理员发送一条测试消息
- 任何一步失败则非零退出，让 Actions 标记为失败
"""

import asyncio
import os
import sys


async def main() -> int:
    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        print("❌ 缺少 BOT_TOKEN 环境变量（请在 GitHub 仓库 Settings → Secrets 中配置）")
        return 1

    # 避免在日志中泄露完整 token
    token_preview = f"{token[:10]}...{token[-4:]}" if len(token) > 14 else "***"
    print(f"使用 token: {token_preview}")

    from aiogram import Bot

    bot = Bot(token=token)
    try:
        me = await bot.get_me()
        print(f"✅ getMe 成功: @{me.username} (ID {me.id})")
        print(f"✅ 机器人可正常连接 Telegram API（本机无需梯子，海外 runner 直连）")
    except Exception as e:
        print(f"❌ getMe 失败: {e}")
        return 1

    admins = [a.strip() for a in os.environ.get("ADMIN_IDS", "").split(",") if a.strip()]
    if admins:
        try:
            await bot.send_message(admins[0], "✅ 机器人连通性验证成功，可以正常收发消息！")
            print(f"✅ 已向管理员 {admins[0]} 发送测试消息")
        except Exception as e:
            print(f"⚠️ 发送测试消息失败（检查 ADMIN_IDS 是否为你的数字 ID）: {e}")
            return 1
    else:
        print("ℹ️ 未配置 ADMIN_IDS，跳过发消息验证")

    await bot.session.close()
    print("🎉 全部验证通过")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
