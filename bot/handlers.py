# bot/handlers.py - для python-telegram-bot==13.15
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CallbackContext
from telegram.error import BadRequest
from database import (
    save_user, get_user, get_services, add_service, delete_service,
    get_user_bookings, add_booking, get_booking_by_id_and_user,
    get_booking_by_id, delete_booking, get_user_by_id,
    get_barber_name, is_closed, get_working_hours, set_working_hours,
    close_day, close_time, open_day, open_time, get_closed_slots
)
from config import ADMINS, TIME_SLOT_MINUTES, ENABLE_ADMIN_NOTIFICATIONS
from datetime import datetime, timedelta
import sqlite3
from contextlib import closing

# Глобальная переменная для уведомлений
application = None

def set_application(app):
    global application
    application = app

async def notify_admins_about_booking(booking_details, user_info):
    """Отправляет уведомление всем админам о новой записи"""
    if not ENABLE_ADMIN_NOTIFICATIONS or not application:
        return
    
    service, date, time, price = booking_details
    full_name, phone = user_info
    
    message = (
        "📢 *НОВАЯ ЗАПИСЬ*\n"
        f"👤 Клиент: {full_name}\n"
        f"📞 Телефон: {phone}\n"
        f"💅 Услуга: {service}\n"
        f"📅 Дата: {date}\n"
        f"⏰ Время: {time}\n"
        f"💰 Стоимость: {price}₽"
    )
    
    for admin_id in ADMINS:
        try:
            await application.bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Не удалось отправить уведомление админу {admin_id}: {e}")

async def notify_admins_about_cancellation(booking_details, user_info, cancelled_by_admin=False):
    """Отправляет уведомление всем админам об отмене записи"""
    if not ENABLE_ADMIN_NOTIFICATIONS or not application:
        return
    
    service, date, time, price = booking_details
    full_name, phone = user_info
    
    cancelled_by = "клиентом" if not cancelled_by_admin else "администратором"
    
    message = (
        f"❌ *ОТМЕНА ЗАПИСИ* ({cancelled_by})\n"
        f"👤 Клиент: {full_name}\n"
        f"📞 Телефон: {phone}\n"
        f"💅 Услуга: {service}\n"
        f"📅 Дата: {date}\n"
        f"⏰ Время: {time}\n"
        f"💰 Стоимость: {price}₽"
    )
    
    for admin_id in ADMINS:
        try:
            await application.bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Не удалось отправить уведомление об отмене админу {admin_id}: {e}")

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    
    if user.id in ADMINS:
        from bot.admin_keyboards import admin_main_menu
        menu = admin_main_menu()
        update.message.reply_text("🛠 Добро пожаловать в панель администратора!", reply_markup=menu)
        return
    
    db_user = get_user(user.id)
    
    if db_user:
        from bot.user_keyboards import user_main_menu
        menu = user_main_menu()
        greeting = f"Привет, {db_user[0]}! 😊"
        update.message.reply_text(greeting, reply_markup=menu)
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 Отправить контакт", callback_data="request_contact")]
        ])
        update.message.reply_text(
            f"Привет! Имя: {user.full_name or 'Клиент'}\n"
            "Пожалуйста, нажмите кнопку ниже, чтобы отправить свой номер.",
            reply_markup=keyboard
        )

def contact_handler(update: Update, context: CallbackContext):
    contact = update.message.contact
    user = update.effective_user
    
    if contact.user_id != user.id:
        update.message.reply_text("Пожалуйста, отправьте свой номер.")
        return
    
    full_name = user.full_name or "Клиент"
    phone_number = contact.phone_number
    save_user(user.id, full_name, phone_number)
    
    from telegram import ReplyKeyboardRemove
    update.message.reply_text(
        "✅ Контакт получен! Теперь вы можете записаться на услугу.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    if user.id in ADMINS:
        from bot.admin_keyboards import admin_main_menu
        menu = admin_main_menu()
        message = "Добро пожаловать в панель администратора!"
    else:
        from bot.user_keyboards import user_main_menu
        menu = user_main_menu()
        message = "Выберите действие:"
        
    update.message.reply_text(message, reply_markup=menu)

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data
    user_id = update.effective_user.id
    is_admin = user_id in ADMINS
    
    if data == "ignore":
        return
    
    if data == "request_contact":
        contact_kb = ReplyKeyboardMarkup(
            [[KeyboardButton("📞 Отправить номер", request_contact=True)]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
        query.message.reply_text(
            "Пожалуйста, нажмите кнопку ниже, чтобы поделиться контактом:",
            reply_markup=contact_kb
        )
        query.message.delete()
        return

    # Базовые обработчики
    if data == "back_to_main":
        if is_admin:
            from bot.admin_keyboards import admin_main_menu
            menu = admin_main_menu()
            text = "Админ-панель:"
        else:
            from bot.user_keyboards import user_main_menu
            menu = user_main_menu()
            text = "Главное меню:"
        query.edit_message_text(text, reply_markup=menu)

    elif data == "my_bookings":
        bookings = get_user_bookings(user_id)
        if not bookings:
            from bot.user_keyboards import user_main_menu
            query.edit_message_text("У вас нет записей.", reply_markup=user_main_menu())
        else:
            buttons = []
            for b in bookings:
                text = f"{b[1]} | {b[2]} в {b[3]} — {b[4]}₽"
                buttons.append([InlineKeyboardButton(text, callback_data=f"view_booking:{b[0]}")])
            buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
            query.edit_message_text("Ваши записи:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "admin_menu" or (is_admin and data == "back_to_main"):
        from bot.admin_keyboards import admin_main_menu
        query.edit_message_text("🛠 Админ-панель:", reply_markup=admin_main_menu())

    else:
        # Для неизвестных команд
        if is_admin:
            from bot.admin_keyboards import admin_main_menu
            menu = admin_main_menu()
        else:
            from bot.user_keyboards import user_main_menu
            menu = user_main_menu()
        query.edit_message_text("Неизвестная команда.", reply_markup=menu)

def admin_command(update: Update, context: CallbackContext):
    if update.effective_user.id not in ADMINS:
        update.message.reply_text("🚫 Доступ запрещён.")
        return
    
    from bot.admin_keyboards import admin_main_menu
    update.message.reply_text("🛠 Админ-панель:", reply_markup=admin_main_menu())

def text_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        return
    
    state = context.user_data.get('awaiting')
    text = update.message.text.strip()
    
    if state == 'add_service':
        try:
            parts = text.split(',')
            if len(parts) != 3:
                raise ValueError
            name = parts[0].strip()
            price = int(parts[1].strip())
            duration = int(parts[2].strip())
            add_service(name, price, duration)
            from bot.admin_keyboards import admin_services_menu
            update.message.reply_text(f"✅ Услуга '{name}' добавлена.", reply_markup=admin_services_menu())
        except:
            from bot.admin_keyboards import back_to_admin
            update.message.reply_text("❌ Формат: Название, цена, длительность", reply_markup=back_to_admin())
        context.user_data['awaiting'] = None
    else:
        from bot.admin_keyboards import admin_main_menu
        update.message.reply_text("Неизвестная команда.", reply_markup=admin_main_menu())
