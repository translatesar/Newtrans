from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db.database import get_db
from bot.messages import WELCOME_MESSAGE, HELP_MESSAGE, STYLE_NAMES, MODE_NAMES
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db = get_db()
    db.register_user(user_id=user.id, username=user.username or "", first_name=user.first_name or "")
    await update.message.reply_text(WELCOME_MESSAGE)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_MESSAGE)


async def style_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton(f"📝 {STYLE_NAMES['faithful']}", callback_data="style_faithful")],
        [InlineKeyboardButton(f"💬 {STYLE_NAMES['natural']}", callback_data="style_natural")],
        [InlineKeyboardButton(f"📋 {STYLE_NAMES['formal']}", callback_data="style_formal")],
        [InlineKeyboardButton(f"🎨 {STYLE_NAMES['literary']}", callback_data="style_literary")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🎨 لطفاً سبک ترجمه مورد نظر خود را انتخاب کنید:", reply_markup=reply_markup)


async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton(f"📄 {MODE_NAMES['source_translation']}", callback_data="mode_source_translation")],
        [InlineKeyboardButton(f"📄 {MODE_NAMES['translation_source']}", callback_data="mode_translation_source")],
        [InlineKeyboardButton(f"📊 {MODE_NAMES['side_by_side']}", callback_data="mode_side_by_side")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📊 لطفاً حالت خروجی PDF را انتخاب کنید:", reply_markup=reply_markup)


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    db = get_db()
    history = db.get_user_history(user_id, limit=5)
    
    if not history:
        await update.message.reply_text("📭 شما هنوز ترجمه‌ای انجام نداده‌اید.")
        return
    
    history_text = "📋 تاریخچه ترجمه‌های اخیر:\n\n"
    for i, item in enumerate(history, 1):
        date = item["created_at"][:16].replace("T", " ")
        source_lang = item["source_lang"]
        style = STYLE_NAMES.get(item["style"], item["style"])
        preview = item["source_text"][:50] + "..." if len(item["source_text"]) > 50 else item["source_text"]
        history_text += f"{i}. [{date}] {source_lang} → فارسی | {style}\n   {preview}\n\n"
    
    await update.message.reply_text(history_text)


async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("📝 لطفاً متن خود را ارسال کنید تا ترجمه را شروع کنم.\nمی‌توانید از /style برای تغییر سبک ترجمه استفاده کنید.")
