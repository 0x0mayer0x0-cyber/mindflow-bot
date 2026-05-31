import os
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup,
    InlineKeyboardButton, LabeledPrice, PreCheckoutQuery)
from app.database import (get_user, create_user, has_access, register_referral,
    add_access_days, get_stats, get_all_user_ids, get_days_left)

logger = logging.getLogger(__name__)
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "YourBot")
CARD_NUMBER = os.getenv("CARD_NUMBER", "2200 0000 0000 0000")
CARD_NAME = os.getenv("CARD_NAME", "Имя Фамилия")
TON_WALLET = os.getenv("TON_WALLET", "UQD...")
SITE_URL = os.getenv("SITE_URL", "https://mindflow.academy")

router_user = Router()
router_admin = Router()

def e(text: str) -> str:
    for c in r"_*[]()~`>#+-=|{}.!":
        text = text.replace(c, f"\\{c}")
    return text

# ════════════════════════════════════════
#  КЛАВИАТУРЫ
# ════════════════════════════════════════

def kb_main(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Урок дня", callback_data="today_guide"),
         InlineKeyboardButton(text="📖 Все курсы", callback_data="all_courses")],
        [InlineKeyboardButton(text="💳 Купить подписку", callback_data="buy_menu")],
        [InlineKeyboardButton(text="📊 Мой кабинет", callback_data="my_cabinet")],
        [InlineKeyboardButton(text="🎁 Пригласить друга", callback_data="referral_info")],
        [InlineKeyboardButton(text="🏆 Топ рефералов", callback_data="top_refs"),
         InlineKeyboardButton(text="❓ FAQ", callback_data="faq")],
        [InlineKeyboardButton(text="🌐 Наш сайт", url=SITE_URL),
         InlineKeyboardButton(text="💬 Поддержка", callback_data="support")],
    ])

def kb_buy():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Карта — 149₽/месяц", callback_data="pay_card")],
        [InlineKeyboardButton(text="⭐ Telegram Stars — 50 звёзд", callback_data="pay_stars")],
        [InlineKeyboardButton(text="💎 TON крипта — 0.5 TON", callback_data="pay_ton")],
        [InlineKeyboardButton(text="🎁 Получить бесплатно", callback_data="referral_info")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")],
    ])

def kb_back():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])

def kb_cabinet(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="my_status"),
         InlineKeyboardButton(text="🎯 Прогресс", callback_data="my_progress")],
        [InlineKeyboardButton(text="🔗 Моя реф. ссылка", callback_data="my_reflink")],
        [InlineKeyboardButton(text="💳 Продлить доступ", callback_data="buy_menu")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")],
    ])

def kb_courses():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 Продуктивность", callback_data="course_0")],
        [InlineKeyboardButton(text="💰 Финансовая грамотность", callback_data="course_1")],
        [InlineKeyboardButton(text="🚀 Запуск бизнеса", callback_data="course_2")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ])

def kb_no_access(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Купить доступ — 149₽", callback_data="buy_menu")],
        [InlineKeyboardButton(text="🎁 Получить бесплатно", callback_data="referral_info")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
    ])

def kb_card_confirm():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил — проверить!", callback_data="card_paid")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="buy_menu")],
    ])

def kb_ton_confirm():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я отправил TON", callback_data="ton_paid")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="buy_menu")],
    ])

def kb_faq():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Как работает бот?", callback_data="faq_how")],
        [InlineKeyboardButton(text="💳 Как оплатить?", callback_data="faq_pay")],
        [InlineKeyboardButton(text="🎁 Как работают рефералы?", callback_data="faq_ref")],
        [InlineKeyboardButton(text="📚 Что входит в курсы?", callback_data="faq_courses")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")],
    ])

def progress_bar(current, total, length=10):
    filled = int((current / total) * length) if total else 0
    return "▓" * filled + "░" * (length - filled)

# ════════════════════════════════════════
#  СТАРТ
# ════════════════════════════════════════

@router_user.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or "Друг"
    args = message.text.split(maxsplit=1)
    ref_param = args[1] if len(args) > 1 else ""
    inviter_id = None
    if ref_param.startswith("ref"):
        try:
            inviter_id = int(ref_param[3:])
            if inviter_id == uid:
                inviter_id = None
        except ValueError:
            pass

    existing = await get_user(uid)
    is_new = existing is None
    if is_new:
        await create_user(uid, username, full_name, invited_by=inviter_id)

    ref_text = ""
    if is_new and inviter_id:
        success = await register_referral(inviter_id, uid)
        if success:
            ref_text = "\n\n🎁 *Реферальный бонус активирован\\!*\nТебе и другу начислено по *7 дней* доступа\\!"
            try:
                inviter = await get_user(inviter_id)
                inv_days = await get_days_left(inviter_id)
                await message.bot.send_message(inviter_id,
                    f"🎉 *По твоей ссылке пришёл новый пользователь\\!*\n\n"
                    f"👤 {e(full_name)}\n"
                    f"🎁 Тебе начислено *\\+7 дней* доступа\\!\n"
                    f"📅 Теперь у тебя: *{inv_days} дней*\n\n"
                    f"Продолжай приглашать — каждый друг \\= \\+7 дней\\! 🚀",
                    parse_mode="MarkdownV2")
            except Exception:
                pass

    days = await get_days_left(uid)
    status = "✅ Активен" if days > 0 else "❌ Нет доступа"
    days_text = f"*{days} дней*" if days > 0 else "*нет доступа*"

    greeting = "👋 С возвращением" if not is_new else "🎉 Добро пожаловать"

    text = (
        f"🧠 *{greeting}, {e(full_name)}\\!*\n\n"
        f"Я твой AI\\-наставник в Telegram\\.\n"
        f"Каждый день — новый гайд по продуктивности, финансам и бизнесу\\.\n"
        f"{ref_text}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📅 Доступ: {days_text} \\| {e(status)}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"💡 *Что умею:*\n"
        f"📚 Выдавать гайды по курсам\n"
        f"💳 Принимать оплату \\(карта/Stars/TON\\)\n"
        f"🎁 Начислять дни за приглашения\n"
        f"📊 Показывать твой прогресс\n\n"
        f"👇 Выбери что хочешь сделать:"
    )
    await message.answer(text, reply_markup=kb_main(uid), parse_mode="MarkdownV2")

# ════════════════════════════════════════
#  ГЛАВНОЕ МЕНЮ
# ════════════════════════════════════════

@router_user.callback_query(F.data == "main_menu")
async def main_menu(call: CallbackQuery):
    uid = call.from_user.id
    days = await get_days_left(uid)
    days_text = f"*{days} дней*" if days > 0 else "*нет доступа*"
    status = "✅" if days > 0 else "❌"
    await call.message.edit_text(
        f"🧠 *MindFlow Academy*\n\n"
        f"{status} Доступ: {days_text}\n\n"
        f"👇 Выбери действие:",
        reply_markup=kb_main(uid), parse_mode="MarkdownV2"
    )
    await call.answer()

# ════════════════════════════════════════
#  МОЙ КАБИНЕТ
# ════════════════════════════════════════

@router_user.callback_query(F.data == "my_cabinet")
async def my_cabinet(call: CallbackQuery):
    uid = call.from_user.id
    user = await get_user(uid)
    days = await get_days_left(uid)
    joined = datetime.fromisoformat(user["joined_at"])
    days_in_bot = (datetime.now() - joined).days + 1
    status = "✅ Активен" if days > 0 else "❌ Нет доступа"
    text = (
        f"👤 *Мой кабинет*\n\n"
        f"🆔 ID: `{uid}`\n"
        f"📅 В боте: *{days_in_bot} дней*\n"
        f"⏰ Доступ: *{days} дней* \\| {e(status)}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📊 Нажми кнопку для подробностей:"
    )
    await call.message.edit_text(text, reply_markup=kb_cabinet(uid), parse_mode="MarkdownV2")
    await call.answer()

# ════════════════════════════════════════
#  СТАТУС
# ════════════════════════════════════════

@router_user.message(Command("status"))
@router_user.callback_query(F.data == "my_status")
async def cmd_status(update):
    msg = update if isinstance(update, Message) else update.message
    uid = update.from_user.id
    user = await get_user(uid)
    days = await get_days_left(uid)
    joined = datetime.fromisoformat(user["joined_at"])
    days_in_bot = (datetime.now() - joined).days + 1
    bot_link = f"https://t.me/{BOT_USERNAME}?start=ref{uid}"
    status = "✅ Активен" if days > 0 else "❌ Нет доступа"
    bar = progress_bar(min(days, 30), 30)
    text = (
        f"📊 *Мой статус*\n\n"
        f"👤 ID: `{uid}`\n"
        f"📅 В боте: *{days_in_bot} дней*\n"
        f"⏰ Осталось доступа: *{days} дней*\n"
        f"📈 {bar} {days}/30\n"
        f"🔑 Статус: {e(status)}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔗 Твоя реф\\. ссылка:\n`{e(bot_link)}`\n\n"
        f"_Каждый приглашённый друг \\= \\+7 дней тебе и ему\\!_"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Продлить доступ", callback_data="buy_menu")],
        [InlineKeyboardButton(text="🎁 Пригласить друга", url=bot_link)],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")],
    ])
    await msg.answer(text, reply_markup=kb, parse_mode="MarkdownV2")
    if isinstance(update, CallbackQuery):
        await update.answer()

# ════════════════════════════════════════
#  ПРОГРЕСС
# ════════════════════════════════════════

@router_user.callback_query(F.data == "my_progress")
async def my_progress(call: CallbackQuery):
    uid = call.from_user.id
    user = await get_user(uid)
    joined = datetime.fromisoformat(user["joined_at"])
    day_num = (datetime.now() - joined).days + 1
    from app.courses import load_courses
    courses = load_courses()
    total = len(courses[0].get("days", [])) if courses else 7
    current = min(day_num, total)
    bar = progress_bar(current, total)
    pct = int((current / total) * 100) if total else 0
    text = (
        f"🎯 *Мой прогресс*\n\n"
        f"📚 Курс: *{e(courses[0]['name']) if courses else 'Продуктивность'}*\n\n"
        f"📅 День {current} из {total}\n"
        f"{bar} {pct}%\n\n"
    )
    for i in range(1, total + 1):
        icon = "✅" if i < current else ("▶️" if i == current else "🔒")
        day_name = courses[0]["days"][i-1]["title"] if courses and i <= len(courses[0]["days"]) else f"День {i}"
        text += f"{icon} {e(day_name)}\n"
    await call.message.edit_text(text, reply_markup=kb_back(), parse_mode="MarkdownV2")
    await call.answer()

# ════════════════════════════════════════
#  РЕФЕРАЛЬНАЯ ССЫЛКА
# ════════════════════════════════════════

@router_user.callback_query(F.data == "my_reflink")
async def my_reflink(call: CallbackQuery):
    uid = call.from_user.id
    bot_link = f"https://t.me/{BOT_USERNAME}?start=ref{uid}"
    text = (
        f"🔗 *Твоя реферальная ссылка:*\n\n"
        f"`{e(bot_link)}`\n\n"
        f"📋 Скопируй и поделись в:\n"
        f"• TikTok \\(в описании видео\\)\n"
        f"• Instagram \\(в сторис и bio\\)\n"
        f"• WhatsApp и Telegram чатах\n\n"
        f"🎁 *За каждого друга:*\n"
        f"• Тебе \\+7 дней доступа\n"
        f"• Другу \\+7 дней доступа\n\n"
        f"♾️ *Без ограничений\\!* Пригласи 10 друзей \\= 70 дней бесплатно\\!"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Поделиться ссылкой", url=f"https://t.me/share/url?url={bot_link}&text=Попробуй%20MindFlow%20Academy%20-%20AI%20наставник%20в%20Telegram%21")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="my_cabinet")],
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="MarkdownV2")
    await call.answer()

# ════════════════════════════════════════
#  ИНФОРМАЦИЯ О РЕФЕРАЛАХ
# ════════════════════════════════════════

@router_user.callback_query(F.data == "referral_info")
async def referral_info(call: CallbackQuery):
    uid = call.from_user.id
    bot_link = f"https://t.me/{BOT_USERNAME}?start=ref{uid}"
    text = (
        f"🎁 *Реферальная программа*\n\n"
        f"Приглашай друзей и получай *бесплатный доступ* без ограничений\\!\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"*Как это работает:*\n\n"
        f"1️⃣ Скопируй свою ссылку ниже\n"
        f"2️⃣ Отправь другу или залей в TikTok/Instagram\n"
        f"3️⃣ Друг переходит и нажимает START\n"
        f"4️⃣ Вы *оба* получаете \\+7 дней мгновенно\\!\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔗 Твоя ссылка:\n`{e(bot_link)}`"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Поделиться", url=f"https://t.me/share/url?url={bot_link}")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")],
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="MarkdownV2")
    await call.answer()

# ════════════════════════════════════════
#  ТОП РЕФЕРАЛОВ
# ════════════════════════════════════════

@router_user.callback_query(F.data == "top_refs")
async def top_refs(call: CallbackQuery):
    text = (
        f"🏆 *Топ пригласивших*\n\n"
        f"🥇 @user1 — 12 друзей \\= 84 дня\n"
        f"🥈 @user2 — 8 друзей \\= 56 дней\n"
        f"🥉 @user3 — 5 друзей \\= 35 дней\n\n"
        f"_Данные обновляются каждый день\\._\n\n"
        f"💪 Стань первым в топе\\!"
    )
    await call.message.edit_text(text, reply_markup=kb_back(), parse_mode="MarkdownV2")
    await call.answer()

# ════════════════════════════════════════
#  ВСЕ КУРСЫ
# ════════════════════════════════════════

@router_user.callback_query(F.data == "all_courses")
async def all_courses(call: CallbackQuery):
    text = (
        f"📖 *Доступные курсы*\n\n"
        f"🧠 *Продуктивность* — 7 дней\n"
        f"Системное мышление, управление временем, привычки\n\n"
        f"💰 *Финансовая грамотность* — 7 дней\n"
        f"Бюджет, инвестиции, пассивный доход\n\n"
        f"🚀 *Запуск бизнеса* — 7 дней\n"
        f"Идея, MVP, первые клиенты\n\n"
        f"_Выбери курс для подробностей:_"
    )
    await call.message.edit_text(text, reply_markup=kb_courses(), parse_mode="MarkdownV2")
    await call.answer()

@router_user.callback_query(F.data.startswith("course_"))
async def course_detail(call: CallbackQuery):
    uid = call.from_user.id
    idx = int(call.data.split("_")[1])
    courses_info = [
        {
            "name": "🧠 Продуктивность",
            "days": ["Основы системного мышления", "Управление временем", "Матрица Эйзенхауэра",
                    "Глубокая работа", "Привычки и рутины", "Энергия и восстановление", "Финальный план"],
            "desc": "Перестань тушить пожары — начни строить системы"
        },
        {
            "name": "💰 Финансы",
            "days": ["Финансовый аудит", "Правило 50/30/20", "Подушка безопасности",
                    "Избавление от долгов", "Введение в инвестиции", "ETF и индексные фонды", "Пассивный доход"],
            "desc": "От хаоса к финансовой свободе за 7 дней"
        },
        {
            "name": "🚀 Бизнес",
            "days": ["Поиск идеи", "Анализ рынка", "Создание MVP",
                    "Первые продажи", "Маркетинг без бюджета", "Масштабирование", "Система автопилота"],
            "desc": "От идеи до первых клиентов за 7 дней"
        }
    ]
    if idx >= len(courses_info):
        await call.answer("Курс не найден")
        return
    c = courses_info[idx]
    text = f"📚 *{e(c['name'])}*\n\n_{e(c['desc'])}_\n\n*Программа курса:*\n\n"
    for i, day in enumerate(c["days"], 1):
        text += f"День {i}: {e(day)}\n"
    has = await has_access(uid)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Начать курс", callback_data="today_guide")] if has
        else [InlineKeyboardButton(text="💳 Купить доступ", callback_data="buy_menu")],
        [InlineKeyboardButton(text="🔙 Все курсы", callback_data="all_courses")],
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="MarkdownV2")
    await call.answer()

# ════════════════════════════════════════
#  УРОК ДНЯ
# ════════════════════════════════════════

@router_user.callback_query(F.data == "today_guide")
async def today_guide(call: CallbackQuery):
    uid = call.from_user.id
    if not await has_access(uid):
        await call.message.edit_text(
            "🔒 *Доступ закрыт*\n\nКупи подписку или пригласи друга и получи \\+7 дней бесплатно\\!",
            reply_markup=kb_no_access(uid), parse_mode="MarkdownV2"
        )
        await call.answer("Нет доступа")
        return
    from app.courses import load_courses, get_day_content
    user = await get_user(uid)
    courses = load_courses()
    if not courses:
        await call.answer("Курсы скоро появятся!")
        return
    joined = datetime.fromisoformat(user["joined_at"])
    day_num = (datetime.now() - joined).days + 1
    course = courses[0]
    content, day_title = get_day_content(course, day_num)
    total = len(course.get("days", []))
    current = min(day_num, total)
    bar = progress_bar(current, total)
    text = (
        f"📚 *{e(course['name'])}*\n"
        f"День {current} из {total} {bar}\n\n"
        f"*{e(day_title)}*\n\n"
        f"{e(content)}\n\n"
        f"_Следующий урок завтра ✨_"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Мой прогресс", callback_data="my_progress")],
        [InlineKeyboardButton(text="📖 Все курсы", callback_data="all_courses")],
        [InlineKeyboardButton(text="🔗 Поделиться", url=f"https://t.me/share/url?url=https://t.me/{BOT_USERNAME}")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")],
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="MarkdownV2")
    await call.answer()

# ════════════════════════════════════════
#  FAQ
# ════════════════════════════════════════

@router_user.callback_query(F.data == "faq")
async def faq(call: CallbackQuery):
    await call.message.edit_text(
        "❓ *Часто задаваемые вопросы*\n\nВыбери вопрос:",
        reply_markup=kb_faq(), parse_mode="MarkdownV2"
    )
    await call.answer()

@router_user.callback_query(F.data == "faq_how")
async def faq_how(call: CallbackQuery):
    text = (
        "❓ *Как работает бот?*\n\n"
        "1️⃣ Нажми /start\n"
        "2️⃣ Купи подписку или пригласи друга\n"
        "3️⃣ Каждый день получай новый гайд\n"
        "4️⃣ Учись в удобное время\n"
        "5️⃣ Зарабатывай дни приглашая друзей\n\n"
        "Всё просто\\! 🚀"
    )
    await call.message.edit_text(text, reply_markup=kb_faq(), parse_mode="MarkdownV2")
    await call.answer()

@router_user.callback_query(F.data == "faq_pay")
async def faq_pay(call: CallbackQuery):
    text = (
        "💳 *Как оплатить?*\n\n"
        "У нас 3 способа оплаты:\n\n"
        "1️⃣ *Карта* — 149₽/месяц\n"
        "Переводишь на карту, нажимаешь \\«Оплатил\\»\n"
        "Доступ открывается за 15 минут\n\n"
        "2️⃣ *Telegram Stars* — 50 звёзд\n"
        "Оплата внутри Telegram, мгновенно\\!\n\n"
        "3️⃣ *TON крипта* — 0\\.5 TON\n"
        "Переводишь на кошелёк, пишешь комментарий"
    )
    await call.message.edit_text(text, reply_markup=kb_faq(), parse_mode="MarkdownV2")
    await call.answer()

@router_user.callback_query(F.data == "faq_ref")
async def faq_ref(call: CallbackQuery):
    text = (
        "🎁 *Как работают рефералы?*\n\n"
        "Всё очень просто:\n\n"
        "🔗 Получи свою ссылку в разделе \\«Пригласить друга\\»\n"
        "📤 Поделись в TikTok, Instagram, WhatsApp\n"
        "✅ Друг переходит и нажимает START\n"
        "🎁 Вы *оба* получаете \\+7 дней\n\n"
        "♾️ Нет ограничений\\!\n"
        "10 друзей \\= 70 дней бесплатно"
    )
    await call.message.edit_text(text, reply_markup=kb_faq(), parse_mode="MarkdownV2")
    await call.answer()

@router_user.callback_query(F.data == "faq_courses")
async def faq_courses(call: CallbackQuery):
    text = (
        "📚 *Что входит в курсы?*\n\n"
        "✅ 3 полных курса по 7 уроков\n"
        "✅ Практические задания каждый день\n"
        "✅ Реальные кейсы и примеры\n"
        "✅ Без воды — только суть\n\n"
        "📌 *Темы:*\n"
        "🧠 Продуктивность и системное мышление\n"
        "💰 Финансовая грамотность и инвестиции\n"
        "🚀 Запуск бизнеса с нуля"
    )
    await call.message.edit_text(text, reply_markup=kb_faq(), parse_mode="MarkdownV2")
    await call.answer()

# ════════════════════════════════════════
#  ПОДДЕРЖКА
# ════════════════════════════════════════

@router_user.callback_query(F.data == "support")
async def support(call: CallbackQuery):
    text = (
        "💬 *Поддержка*\n\n"
        "Если у тебя возникли вопросы:\n\n"
        "📩 Напиши нам: @your\\_support\n"
        "⏰ Отвечаем в течение 2 часов\n\n"
        "Или опиши проблему прямо здесь и нажми кнопку:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📩 Написать в поддержку", url="https://t.me/your_support")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")],
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="MarkdownV2")
    await call.answer()

# ════════════════════════════════════════
#  МЕНЮ ПОКУПКИ
# ════════════════════════════════════════

@router_user.callback_query(F.data == "buy_menu")
async def buy_menu(call: CallbackQuery):
    text = (
        "💳 *Купить подписку*\n\n"
        "📦 *Что входит:*\n"
        "✅ Доступ ко всем курсам на 30 дней\n"
        "✅ 3 курса × 7 уроков \\= 21 гайд\n"
        "✅ Реферальные бонусы\n"
        "✅ Новые курсы каждый месяц\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💰 *Выбери способ оплаты:*"
    )
    await call.message.edit_text(text, reply_markup=kb_buy(), parse_mode="MarkdownV2")
    await call.answer()

# ── ОПЛАТА КАРТОЙ ──
@router_user.callback_query(F.data == "pay_card")
async def pay_card(call: CallbackQuery):
    text = (
        f"💳 *Оплата картой*\n\n"
        f"Переведи *149 рублей* на карту:\n\n"
        f"🏦 Номер карты:\n`{e(CARD_NUMBER)}`\n\n"
        f"👤 Получатель: *{e(CARD_NAME)}*\n\n"
        f"📝 *В комментарии напиши твой ID:*\n"
        f"`{call.from_user.id}`\n\n"
        f"⚡ Доступ открывается за *15 минут*\n"
        f"после подтверждения платежа\\!"
    )
    await call.message.edit_text(text, reply_markup=kb_card_confirm(), parse_mode="MarkdownV2")
    await call.answer()

@router_user.callback_query(F.data == "card_paid")
async def card_paid(call: CallbackQuery):
    uid = call.from_user.id
    username = call.from_user.username or "нет"
    try:
        await call.bot.send_message(OWNER_ID,
            f"💳 *НОВАЯ ОПЛАТА КАРТОЙ\\!*\n\n"
            f"👤 @{e(username)}\n"
            f"🆔 ID: `{uid}`\n"
            f"💰 149₽\n\n"
            f"✅ Выдай доступ командой:\n"
            f"`/admin_add_ref {uid} 30`",
            parse_mode="MarkdownV2")
    except Exception as ex:
        logger.error(f"Ошибка уведомления: {ex}")
    await call.message.edit_text(
        "✅ *Заявка отправлена\\!*\n\n"
        "⏰ Доступ откроется в течение *15 минут*\n"
        "после проверки платежа\\.\n\n"
        "Если прошло больше 15 минут — напиши в /help",
        reply_markup=kb_back(), parse_mode="MarkdownV2"
    )
    await call.answer("Заявка отправлена!")

# ── TELEGRAM STARS ──
@router_user.callback_query(F.data == "pay_stars")
async def pay_stars(call: CallbackQuery):
    await call.message.answer_invoice(
        title="MindFlow Academy — 30 дней",
        description="Полный доступ ко всем курсам на 30 дней",
        payload=f"sub_stars_{call.from_user.id}",
        currency="XTR",
        prices=[LabeledPrice(label="Подписка 30 дней", amount=50)],
    )
    await call.answer()

@router_user.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

@router_user.message(F.successful_payment)
async def successful_payment(message: Message):
    uid = message.from_user.id
    await add_access_days(uid, 30)
    await message.answer(
        "⭐ *Оплата звёздами прошла\\!*\n\n"
        "✅ *30 дней доступа активировано\\!*\n\n"
        "Нажми /start чтобы начать 🚀",
        parse_mode="MarkdownV2"
    )
    try:
        await message.bot.send_message(OWNER_ID,
            f"⭐ Оплата Stars\\!\n🆔 `{uid}`\n✅ \\+30 дней выдано автоматически",
            parse_mode="MarkdownV2")
    except Exception:
        pass

# ── TON ──
@router_user.callback_query(F.data == "pay_ton")
async def pay_ton(call: CallbackQuery):
    text = (
        f"💎 *Оплата TON криптой*\n\n"
        f"Переведи *0\\.5 TON* на кошелёк:\n\n"
        f"`{e(TON_WALLET)}`\n\n"
        f"📝 *В комментарии напиши:*\n"
        f"`MF_{call.from_user.id}`\n\n"
        f"⏰ Доступ открывается за *30 минут*\n"
        f"после проверки транзакции\\!"
    )
    await call.message.edit_text(text, reply_markup=kb_ton_confirm(), parse_mode="MarkdownV2")
    await call.answer()

@router_user.callback_query(F.data == "ton_paid")
async def ton_paid(call: CallbackQuery):
    uid = call.from_user.id
    username = call.from_user.username or "нет"
    try:
        await call.bot.send_message(OWNER_ID,
            f"💎 *НОВАЯ ОПЛАТА TON\\!*\n\n"
            f"👤 @{e(username)}\n"
            f"🆔 ID: `{uid}`\n"
            f"💰 0\\.5 TON\n\n"
            f"✅ После проверки кошелька выдай:\n"
            f"`/admin_add_ref {uid} 30`",
            parse_mode="MarkdownV2")
    except Exception as ex:
        logger.error(f"Ошибка: {ex}")
    await call.message.edit_text(
        "✅ *Заявка на TON отправлена\\!*\n\n"
        "⏰ Доступ откроется за *30 минут*\n"
        "после проверки транзакции\\.",
        reply_markup=kb_back(), parse_mode="MarkdownV2"
    )
    await call.answer("Заявка отправлена!")

# ════════════════════════════════════════
#  ПОМОЩЬ
# ════════════════════════════════════════

@router_user.message(Command("help"))
async def cmd_help(message: Message):
    uid = message.from_user.id
    text = (
        "❓ *Помощь*\n\n"
        "*/start* — главное меню\n"
        "*/status* — мой статус и дни доступа\n"
        "*/help* — эта справка\n\n"
        "💳 Оплата: карта / Stars / TON\n"
        "🎁 Бесплатно: пригласи друга \\= \\+7 дней\n\n"
        "📞 Поддержка: @your\\_support"
    )
    await message.answer(text, reply_markup=kb_main(uid), parse_mode="MarkdownV2")

# ════════════════════════════════════════
#  АДМИН
# ════════════════════════════════════════

@router_admin.message(Command("admin_stats"))
async def admin_stats(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    stats = await get_stats()
    await message.answer(
        f"📊 *Статистика бота*\n\n"
        f"👥 Всего: *{stats['total']}*\n"
        f"✅ Активных: *{stats['active']}*\n"
        f"🔗 Рефералов: *{stats['referrals']}*\n\n"
        f"💰 *Команды:*\n"
        f"/admin\\_broadcast — рассылка\n"
        f"/admin\\_add\\_ref ID DAYS — выдать дни",
        parse_mode="MarkdownV2")

@router_admin.message(Command("admin_broadcast"))
async def admin_broadcast(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /admin_broadcast Текст")
        return
    user_ids = await get_all_user_ids()
    sent, failed = 0, 0
    status_msg = await message.answer(f"⏳ Рассылка {len(user_ids)} пользователям...")
    for uid in user_ids:
        try:
            await message.bot.send_message(uid, e(args[1]), parse_mode="MarkdownV2")
            sent += 1
        except Exception:
            failed += 1
    await status_msg.edit_text(f"✅ Отправлено: {sent}\n❌ Ошибок: {failed}")

@router_admin.message(Command("admin_add_ref"))
async def admin_add_ref(message: Message):
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
        await message.bot.send_message(uid,
            f"✅ *Доступ активирован\\!*\n\n"
            f"🎉 Тебе начислено *{days} дней* доступа\\!\n"
            f"Нажми /start чтобы начать обучение 🚀",
            parse_mode="MarkdownV2")
        await message.answer(f"✅ Пользователю `{uid}` добавлено *{days} дней*\\!", parse_mode="MarkdownV2")
    except Exception as ex:
        await message.answer(f"Ошибка: {ex}")
