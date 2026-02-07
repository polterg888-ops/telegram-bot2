# main.py - РАБОЧАЯ ВЕРСИЯ
import os
import sys
import logging

# Добавим заглушку для imghdr если его нет
try:
    import imghdr
except ImportError:
    # Создаем заглушку для Python 3.13+
    class ImghdrStub:
        def what(self, *args, **kwargs):
            return None
    sys.modules['imghdr'] = ImghdrStub()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция запуска"""
    try:
        print("=" * 60)
        print("🚀 ЗАПУСК ТЕЛЕГРАМ БОТА ДЛЯ БАРБЕРШОПА")
        print("=" * 60)
        
        # 1. Проверка конфига
        try:
            from config import BOT_TOKEN, ADMINS
            logger.info(f"✅ Токен: {'установлен' if BOT_TOKEN else 'НЕТ!'}")
            logger.info(f"✅ Админы: {ADMINS}")
            
            if not BOT_TOKEN:
                logger.error("❌ BOT_TOKEN не установлен!")
                return
                
        except ImportError as e:
            logger.error(f"❌ Ошибка загрузки config.py: {e}")
            return
        
        # 2. Инициализация базы данных
        try:
            from database import init_db
            init_db()
            logger.info("✅ База данных инициализирована")
        except Exception as e:
            logger.error(f"❌ Ошибка базы данных: {e}")
            return
        
        # 3. Создание приложения (версия 20.7)
        try:
            from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
            
            app = Application.builder().token(BOT_TOKEN).build()
            logger.info("✅ Приложение бота создано")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания приложения: {e}")
            return
        
        # 4. Импорт и добавление обработчиков
        try:
            # Импортируем обработчики ПОСЛЕ создания приложения
            from bot.handlers import start, admin_command, contact_handler, button_handler, text_handler, set_application
            
            # Передаем приложение для уведомлений
            set_application(app)
            
            # Добавление обработчиков
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("admin", admin_command))
            app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
            app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, text_handler))
            app.add_handler(CallbackQueryHandler(button_handler))
            
            logger.info("✅ Обработчики добавлены")
            
        except ImportError as e:
            logger.error(f"❌ Ошибка импорта обработчиков: {e}")
            logger.error("Проверьте файлы в папке bot/:")
            logger.error("1. __init__.py (пустой файл)")
            logger.error("2. handlers.py")
            logger.error("3. admin_keyboards.py")
            logger.error("4. user_keyboards.py")
            return
        
        # 5. Запуск бота
        logger.info("=" * 60)
        logger.info("🤖 БОТ ЗАПУЩЕН И ГОТОВ К РАБОТЕ!")
        logger.info("=" * 60)
        
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
        
    except Exception as e:
        logger.error(f"💥 КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
