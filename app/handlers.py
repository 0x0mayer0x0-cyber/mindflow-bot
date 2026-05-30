import os
import logging
from pathlib import Path
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.database import get_user, create_user, has_access, register_referral, add_access_days, get_stats, get_all_user_ids, get_days_left
from app.courses import load_courses, get_day_content

logger = logging.getLogger(__name__)
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "YourBot")

router_user = Router()
router_admin = Router()

def escape_md(text):
    chars = r"_*[]()~`>#+-=|{}.!"
    for c in chars:
        text = text.replace(c, f"\\{c}")
    return text

def main_keyboard(user_id):
    bot_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Читать гайд сегодня", callback_data="today_guide"),
         InlineKeyboardButton(text="📊 Мой прогресс", callback_data="my_status")],
        [InlineKeyboardButton(text="🔗 Пригласить друга (+7 дней)", url=bot_link)],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
    ])

def no_access_keyboard(user_id):
    bot_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Пригласить друга и получить доступ", url=bot_link)],
        [InlineKeyboardButton(text="📊 Мой статус", callback_data="my_status")],
    ])

@router_user.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or ""
    args = message.text.split(maxsplit=1)
    ref_param = args[1] if len(args) > 1 else ""
    inviter_id = None
    if ref_param.startswith("ref"):
        try:
            inviter_id = int(ref_param[3:])
            if inviter_id == user_id:
                inviter_id = None
        except ValueError:
            inviter_id = None
    existing = await get_user(user_id)
    is_new = existing is None
    if is_new:
        await create_user(user_id, username, full_name, invited_by=inviter_id)
    ref_bonus_text = ""
    if is_new and inviter_id:
        success = await register_referral(inviter_id, user_id)
        if success:
            ref_bonus_text = "\n\n🎁 *Реферальный бонус активирован\\!* Тебе и другу начислено по 7 дней\\!"
    days = await get_days_left(user_id)
    days_text = f"*{days} дней*" if days > 0 else "*нет активного доступа*"
    welcome = (f"🧠 *Добро пожаловать в MindFlow Academy\\!*\n\n"
               f"Я твой AI\\-наставник в Telegram\\.\n{ref_bonus_text}\n\n"
               f"📅 Твой доступ: {days_text}\n\n👇 Выбери действие:")
    await message.answer(welcome, reply_markup=main_keyboard(user_id), parse_mode="MarkdownV2")

@router_user.message(Command("status"))
@router_user.callback_query(F.data == "my_status")
async def cmd_status(update):
    msg = update if isinstance(update, Message) else update.message
    user_id = update.from_user.id
    days = await get_days_left(user_id)
    bot_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
    status_emoji = "✅" if days > 0 else "❌"
    text = (f"📊 *Твой статус*\n\n{status_emoji} Дней доступа: *{days}*\n"
            f"🔗 Твоя ссылка:\n`{escape_md(bot_link)}`\n\n"
            f"_За каждого друга \\+7 дней\\!_")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Поделиться ссылкой", url=bot_link)],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")],
    ])
    await msg.answer(text, reply_markup=kb, parse_mode="MarkdownV2")
    if isinstance(update, CallbackQuery):
        await update.answer()

@router_user.message(Command("help"))
@router_user.callback_query(F.data == "help")
async def cmd_help(update):
    msg = update if isinstance(update, Message) else update.message
    user_id = update.from_user.id
    text = ("❓ *Справка*\n\n/start — перезапустить\n/status — мой статус\n/help — помощь\n\n"
            "🎁 Пригласи друга по своей ссылке \\(/status\\) и получи \\+7 дней\\!")
    await msg.answer(text, reply_markup=main_keyboard(user_id), parse_mode="MarkdownV2")
    if isinstance(update, CallbackQuery):
        await update.answer()

@router_user.callback_query(F.data == "main_menu")
async def callback_main_menu(call: CallbackQuery):
    user_id = call.from_user.id
    days = await get_days_left(user_id)
    days_text = f"*{days} дней*" if days > 0 else "*нет активного доступа*"
    await call.message.edit_text(
        f"🧠 *MindFlow Academy*\n\n📅 Твой доступ: {days_text}\n\n👇 Выбери действие:",
        reply_markup=main_keyboard(user_id), parse_mode="MarkdownV2")
    await call.answer()

@router_admin.message(Command("admin_stats"))
async def cmd_admin_stats(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    stats = await get_stats()
    await message.answer(
        f"📊 *Статистика*\n\n👥 Всего: *{stats['total']}*\n✅ Активных: *{stats['active']}*\n🔗 Рефералов: *{stats['referrals']}*",
        parse_mode="MarkdownV2")

@router_admin.message(Command("admin_broadcast"))
async def cmd_admin_broadcast(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /admin_broadcast Текст")
        return
    text = args[1]
    user_ids = await get_all_user_ids()
    sent, failed = 0, 0
    for uid in user_ids:
        try:
            await message.bot.send_message(uid, escape_md(text), parse_mode="MarkdownV2")
            sent += 1
        except Exception as e:
            failed += 1
    await message.answer(f"✅ Отправлено: {sent}\n❌ Ошибок: {failed}")

@router_admin.message(Command("admin_add_ref"))
async def cmd_admin_add_ref(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Использование: /admin_add_ref USER_ID DAYS")
        return
    try:
        uid = int(parts[1])
        days = int(parts[2])
        await add_access_days(uid, days)
        await message.answer(f"✅ Пользователю {uid} добавлено {days} дней\\!", parse_mode="MarkdownV2")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
