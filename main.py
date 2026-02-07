# main.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
import os
import sys
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def main():
    print("=" * 60)
    print("🚀 ЗАПУСК ТЕЛЕГРАМ БОТА")
    print("=" * 60)
    
    # Сначала импортируем config чтобы проверить токен
    try:
        from config import BOT_TOKEN, ADMINS
        logger.info(f"Токен: {'установлен' if BOT_TOKEN else 'НЕТ'}")
        logger.info(f"Админы: {ADMINS}")
    except ImportError as e:
        logger.error(f"Ошибка импорта config: {e}")
        return
    
    # Инициализация БД
    try:
        from database import init_db
        init_db()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка БД: {e}")
        return
    
    # Импорт обработчиков
    try:
        from bot.handlers import (
            start, contact_handler, button_handler, 
            admin_command, text_handler, set_application
        )
        logger.info("✅ Модули бота загружены")
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта модулей бота: {e}")
        logger.error("Проверьте что в папке bot/ есть:")
        logger.error("- __init__.py (пустой файл)")
        logger.error("- handlers.py")
        logger.error("- admin_keyboards.py")
        logger.error("- user_keyboards.py")
        return
    
    # Создание приложения
    try:
        from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
        
        app = Application.builder().token(BOT_TOKEN).build()
        set_application(app)
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("admin", admin_command))
        app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
        app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, text_handler))
        app.add_handler(CallbackQueryHandler(button_handler))
        
        logger.info("✅ Бот запущен и готов к работе!")
        logger.info("=" * 60)
        
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
