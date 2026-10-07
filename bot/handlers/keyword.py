"""关键词自动回复 + 管理面板。

- 管理员：/panel 打开管理面板，通过按钮添加 / 查看 / 删除「关键词 → 回复内容」规则
- 群成员：在群里发消息包含关键词时，机器人自动回复预设内容
"""
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.database import db
from bot.utils import is_admin

router = Router(name="keyword")

MAX_KEYWORD_LEN = 20


class AddKeywordState(StatesGroup):
    waiting = State()


def panel_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ 添加关键词", callback_data="kw:add"),
                InlineKeyboardButton(text="📋 关键词列表", callback_data="kw:list"),
            ],
            [
                InlineKeyboardButton(text="🗑 删除关键词", callback_data="kw:del"),
                InlineKeyboardButton(text="❌ 关闭面板", callback_data="kw:close"),
            ],
        ]
    )


@router.message(Command("panel"), F.chat.type.in_({"group", "supergroup"}))
async def cmd_panel(message: Message, bot: Bot) -> None:
    if not await is_admin(bot, message.chat.id, message.from_user.id):
        await message.answer("⚠️ 只有群管理员才能使用关键词面板。")
        return
    await message.answer(
        "🎛 <b>关键词自动回复面板</b>\n"
        "添加规则后，群成员发言包含关键词即自动回复。\n"
        "回复内容支持占位符 {name}（成员昵称）。",
        reply_markup=panel_markup(),
    )


@router.callback_query(F.data == "kw:add")
async def kw_add(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if not await is_admin(bot, callback.message.chat.id, callback.from_user.id):
        await callback.answer("只有管理员可以操作", show_alert=True)
        return
    await state.set_state(AddKeywordState.waiting)
    await callback.message.answer(
        "请输入规则，格式：<code>关键词|回复内容</code>\n"
        "示例：<code>群规|进群请先看置顶群规，友好发言</code>\n"
        "发 /cancel 可取消。"
    )
    await callback.answer()


@router.message(AddKeywordState.waiting)
async def kw_input(message: Message, state: FSMContext, bot: Bot) -> None:
    if not message.text:
        await message.answer("请发送文字内容")
        return
    if message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("已取消添加。")
        return
    if "|" not in message.text:
        await message.answer("格式不对，请用：<code>关键词|回复内容</code>")
        return
    keyword, reply = message.text.split("|", 1)
    keyword = keyword.strip()
    reply = reply.strip()
    if not keyword or len(keyword) > MAX_KEYWORD_LEN:
        await message.answer(f"关键词不能为空且不超过 {MAX_KEYWORD_LEN} 字")
        return
    if not reply:
        await message.answer("回复内容不能为空")
        return
    await db.add_keyword(message.chat.id, keyword, reply, message.from_user.id)
    await state.clear()
    await message.answer(f"✅ 已添加关键词 <b>{keyword}</b>：{reply}")


@router.callback_query(F.data == "kw:list")
async def kw_list(callback: CallbackQuery, bot: Bot) -> None:
    if not await is_admin(bot, callback.message.chat.id, callback.from_user.id):
        await callback.answer("只有管理员可以操作", show_alert=True)
        return
    rows = await db.get_keywords(callback.message.chat.id)
    if not rows:
        await callback.answer("本群还没有关键词规则")
        return
    lines = ["🎛 <b>本群关键词规则</b>"]
    for i, row in enumerate(rows, 1):
        lines.append(f"{i}. <b>{row['keyword']}</b> → {row['reply']}")
    await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.callback_query(F.data == "kw:del")
async def kw_del_menu(callback: CallbackQuery, bot: Bot) -> None:
    if not await is_admin(bot, callback.message.chat.id, callback.from_user.id):
        await callback.answer("只有管理员可以操作", show_alert=True)
        return
    rows = await db.get_keywords(callback.message.chat.id)
    if not rows:
        await callback.answer("本群还没有关键词规则")
        return
    buttons = []
    for row in rows:
        short = row["keyword"][:MAX_KEYWORD_LEN]
        buttons.append(
            [InlineKeyboardButton(text=f"🗑 {short}", callback_data=f"kw:del:{short}")]
        )
    await callback.message.answer("点击要删除的关键词：", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("kw:del:"))
async def kw_del_confirm(callback: CallbackQuery, bot: Bot) -> None:
    if not await is_admin(bot, callback.message.chat.id, callback.from_user.id):
        await callback.answer("只有管理员可以操作", show_alert=True)
        return
    keyword = callback.data.removeprefix("kw:del:")
    ok = await db.del_keyword(callback.message.chat.id, keyword)
    await callback.message.answer(f"✅ 已删除关键词 <b>{keyword}</b>" if ok else f"❌ 未找到关键词 <b>{keyword}</b>")
    await callback.answer()


@router.callback_query(F.data == "kw:close")
async def kw_close(callback: CallbackQuery) -> None:
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer("面板已关闭")


@router.message(
    F.chat.type.in_({"group", "supergroup"}),
    F.text,
    ~F.text.startswith("/"),
)
async def keyword_trigger(message: Message, bot: Bot) -> None:
    if message.from_user is None or message.from_user.is_bot:
        return
    if message.text and message.text.startswith("/"):
        return
    reply = await db.find_keyword(message.chat.id, message.text.strip())
    if reply:
        name = message.from_user.full_name or message.from_user.first_name
        await message.answer(reply.replace("{name}", name))
