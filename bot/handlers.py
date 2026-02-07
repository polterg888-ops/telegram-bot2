# bot/handlers.py - УПРОЩЕННАЯ ВЕРСИЯ
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from telegram.error import BadRequest

# Глобальная переменная для уведомлений
application = None

def set_application(app):
    global application
    application = app

# Остальные функции пока упростим до базовых
def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id in [7320702445, 800358599]:  # Ваши ID админов
        from bot.admin_keyboards import admin_main_menu
        menu = admin_main_menu()
        update.message.reply_text("🛠 Добро пожаловать в панель администратора!", reply_markup=menu)
        return
    
    # Для обычных пользователей - простое сообщение
    update.message.reply_text(
        "👋 Привет! Я бот для записи в барбершоп.\n\n"
        "Сейчас я настраиваюсь, скоро буду готов к работе!"
    )

def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update.message.reply_text("✅ Контакт получен! Спасибо.")

def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    query.answer()
    query.edit_message_text("⏳ Функция в разработке...")

def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in [7320702445, 800358599]:  # Ваши ID админов
        from bot.admin_keyboards import admin_main_menu
        update.message.reply_text("🛠 Админ-панель:", reply_markup=admin_main_menu())
    else:
        update.message.reply_text("🚫 Доступ запрещён.")

def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update.message.reply_text("📝 Я получил ваше сообщение. Скоро буду полностью функционален!")
