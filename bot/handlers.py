import os
import tempfile
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import settings
from db.database import get_db
from services.translation import TranslationService
from services.speech import SpeechService
from services.file_handler import FileHandler
from pdf.generator import PDFGenerator
from bot.messages import (
    PROCESSING_VOICE, PROCESSING_TRANSLATION, PROCESSING_PDF, PROCESSING_FILE,
    ERROR_GENERAL, ERROR_FILE_TOO_LARGE, ERROR_VOICE_TOO_LONG, ERROR_UNSUPPORTED_FORMAT,
    SOURCE_DETECTED, TRANSLATION_COMPLETE, STYLE_NAMES, MODE_NAMES, ERROR_ALREADY_PERSIAN,
)
from utils.logger import setup_logger
from utils.language import detect_language, is_persian

logger = setup_logger(__name__)

from bot.commands import (
    start_command, help_command, style_command, mode_command,
    history_command, translate_command,
)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text
    
    if len(text.encode('utf-8')) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        await update.message.reply_text(ERROR_FILE_TOO_LARGE.format(settings.MAX_FILE_SIZE_MB))
        return
    
    source_lang = detect_language(text)
    
    if is_persian(source_lang):
        keyboard = [
            [InlineKeyboardButton("🔄 بازنویسی", callback_data="action_rewrite"),
             InlineKeyboardButton("📝 خلاصه", callback_data="action_summarize")],
            [InlineKeyboardButton("🌍 ترجمه به عربی", callback_data="action_translate_ar"),
             InlineKeyboardButton("🌍 ترجمه به انگلیسی", callback_data="action_translate_en")],
        ]
        await update.message.reply_text(ERROR_ALREADY_PERSIAN, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    progress_msg = await update.message.reply_text(f"{SOURCE_DETECTED.format(source_lang)}\n{PROCESSING_TRANSLATION}")
    
    try:
        db = get_db()
        user_prefs = db.get_user_preferences(user_id)
        style = user_prefs.get("style", "natural")
        
        translation_service = TranslationService()
        result = await translation_service.translate(
            text=text, source_lang=source_lang, target_lang="fa", style=style,
        )
        
        await progress_msg.edit_text(PROCESSING_PDF)
        
        pdf_gen = PDFGenerator()
        pdf_path = pdf_gen.generate_translation_pdf(
            source_text=text, translated_text=result["translated_text"],
            source_lang=source_lang, target_lang="fa", style=style,
            mode=user_prefs.get("mode", "source_translation"),
        )
        
        db.save_translation(
            user_id=user_id, source_text=text, translated_text=result["translated_text"],
            source_lang=source_lang, target_lang="fa", style=style,
            provider=result.get("provider", "unknown"),
        )
        
        await progress_msg.delete()
        
        message_text = (
            f"{TRANSLATION_COMPLETE}\n\n"
            f"📝 متن اصلی:\n{text[:200]}...\n\n"
            f"🔄 ترجمه:\n{result['translated_text'][:200]}..."
        )
        await update.message.reply_text(message_text)
        
        with open(pdf_path, "rb") as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                filename=f"translation_{user_id}_{source_lang}_fa.pdf",
                caption="📄 ترجمه شما به صورت PDF",
            )
        
        os.unlink(pdf_path)
        
    except Exception as e:
        logger.error(f"Translation error: {e}", exc_info=True)
        await progress_msg.edit_text(ERROR_GENERAL)


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _handle_audio_message(update, context, is_voice=True)


async def handle_audio_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _handle_audio_message(update, context, is_voice=False)


async def _handle_audio_message(update: Update, context: ContextTypes.DEFAULT_TYPE, is_voice: bool) -> None:
    user_id = update.effective_user.id
    
    if is_voice:
        file_obj = update.message.voice
        duration = file_obj.duration
    else:
        file_obj = update.message.audio
        duration = file_obj.duration
    
    if duration > settings.MAX_VOICE_DURATION_SECONDS:
        await update.message.reply_text(ERROR_VOICE_TOO_LONG.format(settings.MAX_VOICE_DURATION_SECONDS))
        return
    
    if file_obj.file_size and file_obj.file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        await update.message.reply_text(ERROR_FILE_TOO_LARGE.format(settings.MAX_FILE_SIZE_MB))
        return
    
    progress_msg = await update.message.reply_text(PROCESSING_VOICE)
    
    try:
        file = await context.bot.get_file(file_obj.file_id)
        
        with tempfile.NamedTemporaryFile(suffix=".ogg" if is_voice else ".mp3", delete=False) as tmp:
            await file.download_to_drive(tmp.name)
            audio_path = tmp.name
        
        speech_service = SpeechService()
        transcription = await speech_service.transcribe(audio_path)
        os.unlink(audio_path)
        
        if not transcription.strip():
            await progress_msg.edit_text("❌ متن قابل تشخیصی در صوت یافت نشد.")
            return
        
        source_lang = detect_language(transcription)
        
        await progress_msg.edit_text(
            f"🎤 متن تشخیص داده شده:\n{transcription[:200]}...\n\n"
            f"{SOURCE_DETECTED.format(source_lang)}\n{PROCESSING_TRANSLATION}"
        )
        
        db = get_db()
        user_prefs = db.get_user_preferences(user_id)
        style = user_prefs.get("style", "natural")
        
        translation_service = TranslationService()
        result = await translation_service.translate(
            text=transcription, source_lang=source_lang, target_lang="fa", style=style,
        )
        
        await progress_msg.edit_text(PROCESSING_PDF)
        
        pdf_gen = PDFGenerator()
        pdf_path = pdf_gen.generate_translation_pdf(
            source_text=transcription, translated_text=result["translated_text"],
            source_lang=source_lang, target_lang="fa", style=style,
            mode=user_prefs.get("mode", "source_translation"),
        )
        
        db.save_translation(
            user_id=user_id, source_text=transcription, translated_text=result["translated_text"],
            source_lang=source_lang, target_lang="fa", style=style,
            provider=result.get("provider", "unknown"),
        )
        
        await progress_msg.delete()
        
        await update.message.reply_text(
            f"{TRANSLATION_COMPLETE}\n\n"
            f"🎤 متن اصلی:\n{transcription}\n\n"
            f"🔄 ترجمه:\n{result['translated_text'][:300]}..."
        )
        
        with open(pdf_path, "rb") as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                filename=f"voice_translation_{user_id}.pdf",
                caption="📄 ترجمه صوت شما به صورت PDF",
            )
        
        os.unlink(pdf_path)
        
    except Exception as e:
        logger.error(f"Voice processing error: {e}", exc_info=True)
        await progress_msg.edit_text(ERROR_GENERAL)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    document = update.message.document
    
    if document.file_size and document.file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        await update.message.reply_text(ERROR_FILE_TOO_LARGE.format(settings.MAX_FILE_SIZE_MB))
        return
    
    file_name = document.file_name or ""
    file_handler = FileHandler()
    
    if not file_handler.is_supported(file_name):
        await update.message.reply_text(ERROR_UNSUPPORTED_FORMAT)
        return
    
    progress_msg = await update.message.reply_text(PROCESSING_FILE)
    
    try:
        file = await context.bot.get_file(document.file_id)
        
        with tempfile.NamedTemporaryFile(suffix=Path(file_name).suffix, delete=False) as tmp:
            await file.download_to_drive(tmp.name)
            file_path = tmp.name
        
        text = await file_handler.extract_text(file_path)
        os.unlink(file_path)
        
        if not text.strip():
            await progress_msg.edit_text("❌ متنی در فایل یافت نشد.")
            return
        
        await progress_msg.edit_text(PROCESSING_TRANSLATION)
        
        source_lang = detect_language(text)
        
        db = get_db()
        user_prefs = db.get_user_preferences(user_id)
        style = user_prefs.get("style", "natural")
        
        translation_service = TranslationService()
        result = await translation_service.translate(
            text=text, source_lang=source_lang, target_lang="fa", style=style,
        )
        
        await progress_msg.edit_text(PROCESSING_PDF)
        
        pdf_gen = PDFGenerator()
        pdf_path = pdf_gen.generate_translation_pdf(
            source_text=text[:5000], translated_text=result["translated_text"][:5000],
            source_lang=source_lang, target_lang="fa", style=style,
            mode=user_prefs.get("mode", "source_translation"),
        )
        
        db.save_translation(
            user_id=user_id, source_text=text[:1000], translated_text=result["translated_text"][:1000],
            source_lang=source_lang, target_lang="fa", style=style,
            provider=result.get("provider", "unknown"),
        )
        
        await progress_msg.delete()
        await update.message.reply_text(f"{TRANSLATION_COMPLETE}\n📄 فایل: {file_name}\n🌍 زبان: {source_lang}")
        
        with open(pdf_path, "rb") as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                filename=f"file_translation_{Path(file_name).stem}.pdf",
                caption="📄 ترجمه فایل شما به صورت PDF",
            )
        
        os.unlink(pdf_path)
        
    except Exception as e:
        logger.error(f"Document processing error: {e}", exc_info=True)
        await progress_msg.edit_text(ERROR_GENERAL)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    db = get_db()
    data = query.data
    
    if data.startswith("style_"):
        style = data.replace("style_", "")
        db.update_user_preferences(user_id, style=style)
        await query.edit_message_text(f"✅ سبک ترجمه به «{STYLE_NAMES[style]}» تغییر کرد.")
    
    elif data.startswith("mode_"):
        mode = data.replace("mode_", "")
        db.update_user_preferences(user_id, mode=mode)
        await query.edit_message_text(f"✅ حالت خروجی به «{MODE_NAMES[mode]}» تغییر کرد.")
    
    elif data.startswith("action_"):
        action = data.replace("action_", "")
        await query.edit_message_text(f"🔄 درخواست {action} دریافت شد. لطفاً متن خود را ارسال کنید.")
        context.user_data["pending_action"] = action


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)
    if update and hasattr(update, "effective_message"):
        try:
            await update.effective_message.reply_text(ERROR_GENERAL)
        except Exception:
            pass
