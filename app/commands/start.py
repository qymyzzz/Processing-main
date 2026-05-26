import os
import queue
from datetime import timedelta, timezone

from dotenv import load_dotenv
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

SUPPORT_IDS = os.getenv("SUPPORT_IDS").split(",")


HELP_CLIENT = """
📖 <b>Меню пользователя</b>
 
🎫 <b>/tickets</b> — посмотреть ваши тикеты
   В групповом чате: показывает тикеты по этой группе.
   В личном чате: показывает ваши личные тикеты.
📅 <b>/tickets</b> — /tickets ДД.ММ.ГГГГ-ДД.ММ.ГГГГ
   В групповом чате: показывает тикеты по этой группе.
   В личном чате: показывает ваши личные тикеты.
🔍 <b>/close</b> — /close &lt;id&gt; → закрыть тикет через меню
🎫 <b>/duty</b> — список дежурных
""".strip()

HELP_SUPPORT = """
🛠 <b>Меню поддержки</b>
 
🎫 <b>/tickets</b> — все тикеты (если в чате, то все тикеты этого чата)
📅 <b>/tickets</b> — /tickets ДД.ММ.ГГГГ-ДД.ММ.ГГГГ
🔍 <b>/close</b> — /close &lt;id&gt; → закрыть тикет через меню
📊 <b>/report</b> — выгрузить все тикеты в Excel
🎫 <b>/duty</b> — список дежурных
🎫 <b>/mytickets</b> — список тикетов за которые вы отвечаете
""".strip()


def support_keyboard() -> ReplyKeyboardMarkup:
    """Полное меню для команды поддержки."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("/tickets")],
            [KeyboardButton("/close")],
            [KeyboardButton("/report")],
            [KeyboardButton("/duty")],
            [KeyboardButton("/mytickets")],
        ],
        resize_keyboard=True,
    )


def client_keyboard() -> ReplyKeyboardMarkup:
    """Базовое меню для клиентов."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("/tickets")],
            [KeyboardButton("/close")],
            [KeyboardButton("/duty")],
        ],
        resize_keyboard=True,
    )


def get_role(user_id: int) -> str:
    """Return 'support', or 'client'."""
    if str(user_id) in SUPPORT_IDS:
        return "support"
    return "client"


def get_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    role = get_role(user_id)
    if role == "support":
        return support_keyboard()
    return client_keyboard()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    role = get_role(user.id)
    keyboard = get_keyboard(user.id)

    if role == "support":
        greeting = (
            f"👋 Добро пожаловать, <b>{user.first_name}</b>!\n"
            "Вы вошли как <b>Поддержка</b>.\n\n" + HELP_SUPPORT
        )
    else:
        greeting = f"👋 Привет, <b>{user.first_name}</b>!\n\n" + HELP_CLIENT

    await update.message.reply_html(greeting, reply_markup=keyboard)
