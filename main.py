# main.py - Telegram Bot для барбершопа
import os
import sys
import logging
import atexit
import signal
import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Настройка логирования для Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Импорт собственных модулей
from database import init_db
from config import BOT_TOKEN
from bot.handlers import start, contact_handler, button_handler, admin_command, text_handler, set_application

# Глобальная переменная для хранения app
bot_application = None

def handle_shutdown(signum, frame):
    """Обработчик сигналов завершения"""
    logger.info(f"Получен сигнал {signum}, завершаем работу бота...")
    if bot_application and bot_application.running:
        bot_application.stop()
    sys.exit(0)

def cleanup():
    """Очистка при завершении"""
    logger.info("Бот завершает работу...")
    logger.info("=" * 50)

# Регистрация обработчиков завершения
atexit.register(cleanup)
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

def check_monthly_restart():
    """
    Проверяет, не пора ли перезапуститься для сброса часов на Render.
    Render дает 750 бесплатных часов в месяц.
    Перезапуск 1 числа каждого месяца.
    """
    now = datetime.datetime.now()
    
    # Проверяем, 1-е ли число месяца
    if now.day == 1 and now.hour < 6:  # 1 число, до 6 утра
        logger.info("1 число месяца - выполняем плановый перезапуск для сброса часов")
        logger.info(f"Render: 750 часов = {750/24:.1f} дней работы в месяц")
        
        # Ждем немного чтобы все логи записались
        import time
        time.sleep(5)
        
        # Завершаем процесс - Render автоматически перезапустит
        os._exit(0)
    
    return False

def create_application():
    """Создание и настройка приложения бота"""
    logger.info("=" * 50)
    logger.info("Создание Telegram бота...")
    logger.info(f"Токен: {'установлен' if BOT_TOKEN else 'НЕ НАЙДЕН!'}")
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не найден! Проверьте переменные окружения.")
        raise ValueError("BOT_TOKEN не установлен")
    
    # Создаем приложение
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Передаем application в handlers для уведомлений
    set_application(app)
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, text_handler))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("Обработчики успешно добавлены")
    return app

def main():
    """Основная функция запуска бота"""
    try:
        # Проверяем перезапуск по месяцу
        if check_monthly_restart():
            return
        
        # Инициализируем базу данных
        logger.info("Инициализация базы данных...")
        init_db()
        logger.info("База данных готова")
        
        # Создаем приложение бота
        global bot_application
        bot_application = create_application()
        
        # Запускаем бота
        logger.info("Запуск бота...")
        logger.info(f"Бот запущен в {datetime.datetime.now()}")
        logger.info("=" * 50)
        
        # Информация о Render
        logger.info("Render.com: 750 бесплатных часов/месяц")
        logger.info(f"Хватит на {750/24:.1f} дней непрерывной работы")
        logger.info("=" * 50)
        
        # Запускаем поллинг
        bot_application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            close_loop=False
        )
        
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
        
        # Подробное логирование для отладки
        logger.error("=" * 50)
        logger.error("Информация для отладки:")
        logger.error(f"Python версия: {sys.version}")
        logger.error(f"Токен установлен: {'Да' if BOT_TOKEN else 'Нет'}")
        logger.error(f"Текущая директория: {os.getcwd()}")
        logger.error(f"Файлы в директории: {os.listdir('.')}")
        
        # Пробуем импортировать модули для проверки
        try:
            from database import init_db
            logger.error("Модуль database: ✓")
        except ImportError as ie:
            logger.error(f"Модуль database: ✗ {ie}")
            
        try:
            from config import ADMINS
            logger.error(f"ADMINS: {ADMINS}")
        except ImportError as ie:
            logger.error(f"Модуль config: ✗ {ie}")
        
        logger.error("=" * 50)
        
        # Ждем перед перезапуском
        import time
        time.sleep(10)
        
        # Поднимаем исключение - Render перезапустит
        raise

if __name__ == '__main__':
    # Выводим информацию о запуске
    print("=" * 60)
    print("Telegram Bot для барбершопа")
    print("Автоматическая система записи")
    print(f"Запуск: {datetime.datetime.now()}")
    print("=" * 60)
    
    # Проверяем переменные окружения
    if not os.getenv("BOT_TOKEN"):
        print("⚠️  ВНИМАНИЕ: BOT_TOKEN не установлен!")
        print("Добавьте в переменные окружения:")
        print("  BOT_TOKEN=ваш_токен")
        print("  ADMINS=ваш_id,второй_id")
        print("  TIMEZONE=Europe/Moscow")
        print("=" * 60)
    
    # Запускаем бота
    try:
        main()
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
    except Exception as e:
        print(f"\nБот завершился с ошибкой: {e}")
        print("Перезапуск через 5 секунд...")
        import time
        time.sleep(5)
        
        # Пробуем перезапуститься
        os.execv(sys.executable, ['python'] + sys.argv)