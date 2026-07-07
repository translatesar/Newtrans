#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from config import settings
from bot.handlers import (
    start_command,
    help_command,
    style_command,
    mode_command,
    history_command,
    translate_command,
    handle_text_message,
    handle_voice_message,
    handle_audio_file,
    handle_document,
    handle_callback_query,
    error_handler,
)
from db.database import init_db
from utils.logger import setup_logger

logger = setup_logger(__name__)


def build_application() -> Application:
    init_db()
    application = Application.builder().token(settings.BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("style", style_command))
    application.add_handler(CommandHandler("mode", mode_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("translate", translate_command))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio_file))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_error_handler(error_handler)
    
    return application


async def main() -> None:
    application = build_application()
    logger.info("Starting bot in polling mode...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    stop_signal = asyncio.Event()
    try:
        await stop_signal.wait()
    except asyncio.CancelledError:
        pass
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
