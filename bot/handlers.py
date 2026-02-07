from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from database import (
    save_user, get_user, get_services, add_service, delete_service,
    get_user_bookings, get_all_bookings, add_booking,
    get_booking_by_id_and_user, get_booking_by_id,
    delete_booking,
    get_barber, update_barber, get_barber_name,
    is_closed,
    get_working_hours, set_working_hours,
    close_day, close_time, open_day, open_time, get_closed_slots,
    get_user_by_id
)
from bot.user_keyboards import (
    user_main_menu, service_menu, generate_user_calendar, 
    time_menu, booking_detail_menu
)
from bot.admin_keyboards import *
from config import ADMINS, TIME_SLOT_MINUTES, ENABLE_ADMIN_NOTIFICATIONS
from datetime import datetime, timedelta
import sqlite3
from contextlib import closing

# Глобальная переменная для хранения application (для отправки уведомлений)
application = None

def set_application(app):
    global application
    application = app

def format_phone_for_display(phone):
    """Форматирует телефон для красивого отображения"""
    # Убираем все нецифровые символы
    clean_phone = ''.join(filter(str.isdigit, phone))
    
    # Форматируем в российский формат
    if len(clean_phone) == 11:
        if clean_phone.startswith('7'):
            return f"+7 {clean_phone[1:4]} {clean_phone[4:7]} {clean_phone[7:]}"
        elif clean_phone.startswith('8'):
            return f"+7 {clean_phone[1:4]} {clean_phone[4:7]} {clean_phone[7:]}"
    elif len(clean_phone) == 10:
        return f"+7 {clean_phone[0:3]} {clean_phone[3:6]} {clean_phone[6:]}"
    
    # Если не удалось отформатировать, возвращаем как есть
    return phone

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

def safe_edit_message(query, text, reply_markup=None, parse_mode=None):
    try:
        current_text = query.message.text or query.message.caption
        
        # Проверяем, изменился ли текст или разметка
        text_changed = current_text != text
        markup_changed = (reply_markup and query.message.reply_markup != reply_markup)
        
        if not text_changed and not markup_changed:
            return
        
        # Используем kwargs для передачи опциональных параметров
        kwargs = {}
        if parse_mode:
            kwargs['parse_mode'] = parse_mode
        if reply_markup:
            kwargs['reply_markup'] = reply_markup
            
        return query.edit_message_text(text=text, **kwargs)
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise

def parse_time(time_str):
    if ':' not in time_str:
        time_str += ":00"
    h, m = time_str.split(':')
    return f"{int(h):02d}:{int(m):02d}"

def is_work_day(date_str):
    """Проверяем, рабочий ли это день (не понедельник и не закрыт)"""
    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    weekday = date_obj.weekday()  # 0 = понедельник, 1 = вторник, ...
    
    # Понедельник - нерабочий день
    if weekday == 0:
        return False
    
    # Проверяем, не закрыт ли весь день
    if is_closed(date_str, None):
        return False
    
    return True

def get_available_times(date_str, duration_minutes):
    """Получаем доступное время для записи с учетом рабочих дней"""
    
    # Проверяем, рабочий ли это день
    if not is_work_day(date_str):
        return []
    
    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    today = datetime.today().date()
    now = datetime.now()
    
    # Получаем рабочее время
    start_time, end_time = get_working_hours()
    start_dt = datetime.combine(date_obj, datetime.strptime(start_time, "%H:%M").time())
    end_dt = datetime.combine(date_obj, datetime.strptime(end_time, "%H:%M").time())
    step = timedelta(minutes=TIME_SLOT_MINUTES)
    
    candidate_slots = []
    current = start_dt
    while current + timedelta(minutes=duration_minutes) <= end_dt:
        candidate_slots.append(current)
        current += step
    
    available = []
    for slot_start in candidate_slots:
        time_str = slot_start.strftime("%H:%M")
        
        # Пропускаем прошедшее время для сегодня
        if date_obj == today and slot_start.time() <= now.time():
            continue
        
        # Проверяем закрыт ли конкретный слот времени
        if is_closed(date_str, time_str):
            continue
        
        # Проверяем пересечение с существующими записями
        slot_end = slot_start + timedelta(minutes=duration_minutes)
        overlap = False
        
        with closing(sqlite3.connect('bot.db')) as conn:
            rows = conn.execute("""
                SELECT b.time, s.duration
                FROM bookings b
                JOIN services s ON b.service = s.name
                WHERE b.date = ?
            """, (date_str,)).fetchall()
            
            for booked_time_str, booked_duration in rows:
                booked_start = datetime.combine(date_obj, datetime.strptime(booked_time_str, "%H:%M").time())
                booked_end = booked_start + timedelta(minutes=booked_duration)
                if slot_start < booked_end and slot_end > booked_start:
                    overlap = True
                    break
        
        if not overlap:
            available.append(time_str)
    
    return available

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Для админа сразу показываем меню
    if user.id in ADMINS:
        menu = admin_main_menu()
        await update.message.reply_text("🛠 Добро пожаловать в панель администратора!", reply_markup=menu)
        return
    
    # Для обычных пользователей
    db_user = get_user(user.id)
    
    if db_user:
        menu = user_main_menu()
        greeting = f"Привет, {db_user[0]}! 😊"
        await update.message.reply_text(greeting, reply_markup=menu)
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 Отправить контакт", callback_data="request_contact")]
        ])
        await update.message.reply_text(
            f"Привет! Имя: {user.full_name or 'Клиент'}\n"
            "Пожалуйста, нажмите кнопку ниже, чтобы отправить свой номер.",
            reply_markup=keyboard
        )

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    user = update.effective_user
    
    # Проверяем, что контакт принадлежит пользователю
    if contact.user_id != user.id:
        await update.message.reply_text("Пожалуйста, отправьте свой номер.")
        return
    
    # Сохраняем пользователя
    full_name = user.full_name or "Клиент"
    phone_number = contact.phone_number
    
    # Сохраняем в базу данных
    save_user(user.id, full_name, phone_number)
    
    # Убираем клавиатуру с кнопкой контакта
    from telegram import ReplyKeyboardRemove
    await update.message.reply_text(
        "✅ Контакт получен! Теперь вы можете записаться на услугу.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Показываем главное меню
    menu = admin_main_menu() if user.id in ADMINS else user_main_menu()
    
    # Разные сообщения после регистрации
    if user.id in ADMINS:
        message = "Добро пожаловать в панель администратора!"
    else:
        message = "Выберите действие:"
        
    # Отправляем новое сообщение с меню
    await update.message.reply_text(message, reply_markup=menu)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    is_admin = user_id in ADMINS
    
    # Игнорируем нажатия на неактивные кнопки
    if data == "ignore":
        return
    
    # Обработчик кнопки "Отправить контакт"
    if data == "request_contact":
        contact_kb = ReplyKeyboardMarkup(
            [[KeyboardButton("📞 Отправить номер", request_contact=True)]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
        await query.message.reply_text(
            "Пожалуйста, нажмите кнопку ниже, чтобы поделиться контактом:",
            reply_markup=contact_kb
        )
        await query.message.delete()
        return

    # Основные команды пользователя
    if data == "back_to_main":
        menu = admin_main_menu() if is_admin else user_main_menu()
        text = "Админ-панель:" if is_admin else "Главное меню:"
        await safe_edit_message(query, text, menu)

    elif data == "my_bookings":
        bookings = get_user_bookings(user_id)
        if not bookings:
            await safe_edit_message(query, "У вас нет записей.", user_main_menu())
        else:
            buttons = []
            for b in bookings:
                text = f"{b[1]} | {b[2]} в {b[3]} — {b[4]}₽"
                buttons.append([InlineKeyboardButton(text, callback_data=f"view_booking:{b[0]}")])
            buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
            await query.edit_message_text("Ваши записи:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("view_booking:"):
        booking_id = int(data.split(":", 1)[1])
        booking = get_booking_by_id_and_user(booking_id, user_id)
        if not booking:
            await safe_edit_message(query, "Запись не найдена.", user_main_menu())
            return
        service, date, time, price = booking
        await query.edit_message_text(
            f"📅 Ваша запись:\nУслуга: {service}\nДата: {date}\nВремя: {time}\nСтоимость: {price}₽",
            reply_markup=booking_detail_menu(booking_id)
        )

    elif data.startswith("cancel_booking:"):
        booking_id = int(data.split(":", 1)[1])
        booking = get_booking_by_id_and_user(booking_id, user_id)
        if not booking:
            await safe_edit_message(query, "❌ Запись не найдена.", user_main_menu())
            return
        
        # Получаем данные записи перед удалением
        service, date, time, price = booking
        
        # Получаем информацию о пользователе
        user = get_user(user_id)
        if user:
            full_name, phone = user
            user_info = (full_name, phone)
            booking_details = (service, date, time, price)
        
        # Удаляем запись
        delete_booking(booking_id)
        
        # Отправляем уведомление админам об отмене КЛИЕНТОМ
        if user:
            await notify_admins_about_cancellation(booking_details, user_info, cancelled_by_admin=False)
        
        await safe_edit_message(query, "✅ Запись отменена.", user_main_menu())

    elif data == "book":
        services = get_services()
        if not services:
            await safe_edit_message(query, "Нет доступных услуг.", user_main_menu())
            return
        await safe_edit_message(query, "Выберите услугу:", service_menu(services))

    elif data.startswith("select_service:"):
        service = data.split(":", 1)[1]
        context.user_data['service'] = service
        for name, price, duration in get_services():
            if name == service:
                context.user_data['price'] = price
                context.user_data['duration'] = duration
                break
        else:
            await safe_edit_message(query, "Услуга не найдена.", user_main_menu())
            return
        
        today = datetime.today()
        await query.edit_message_text(
            "📅 *Выберите дату для записи:*\n\n"
            "🟢 — доступные дни\n"
            "❌ — прошедшие дни\n"
            "🚫 — понедельники (нерабочие дни)",
            parse_mode='Markdown',
            reply_markup=generate_user_calendar(today.year, today.month)
        )

    elif data.startswith("user_calendar_nav:"):
        parts = data.split(":")
        if len(parts) != 3:
            return
        year = int(parts[1])
        month = int(parts[2])
        await query.edit_message_text(
            "📅 *Выберите дату для записи:*\n\n"
            "🟢 — доступные дни\n"
            "❌ — прошедшие дни\n"
            "🚫 — понедельники (нерабочие дни)",
            parse_mode='Markdown',
            reply_markup=generate_user_calendar(year, month)
        )

    elif data.startswith("user_calendar_select:"):
        parts = data.split(":")
        if len(parts) != 2:
            return
        date = parts[1]
        
        # Проверяем, рабочий ли это день
        if not is_work_day(date):
            await safe_edit_message(query, "❌ Этот день не доступен для записи.", user_main_menu())
            return
            
        context.user_data['date'] = date
        
        duration = context.user_data.get('duration')
        if not duration:
            service = context.user_data.get('service')
            for name, price, dur in get_services():
                if name == service:
                    duration = dur
                    context.user_data['duration'] = dur
                    break
        
        times = get_available_times(date, duration)
        if not times:
            await safe_edit_message(query, "📭 Нет свободного времени в этот день.", user_main_menu())
            return
        
        await safe_edit_message(
            query,
            f"📅 *Дата: {date}*\n🕐 *Выберите время:*",
            parse_mode='Markdown',
            reply_markup=time_menu(times)
        )

    elif data == "select_date_back":
        # Вернуться к выбору даты
        today = datetime.today()
        await query.edit_message_text(
            "📅 *Выберите дату для записи:*\n\n"
            "🟢 — доступные дни\n"
            "❌ — прошедшие дни\n"
            "🚫 — понедельники (нерабочие дни)",
            parse_mode='Markdown',
            reply_markup=generate_user_calendar(today.year, today.month)
        )

    elif data.startswith("select_time:"):
        time = data.split(":", 1)[1]
        context.user_data['time'] = time
        service = context.user_data['service']
        price = context.user_data['price']
        
        barber_name = get_barber_name()
        await query.edit_message_text(
            f"*Подтвердите запись:*\n\n"
            f"👨‍💼 *Мастер:* {barber_name}\n"
            f"💅 *Услуга:* {service}\n"
            f"🗓 *Дата:* {context.user_data['date']}\n"
            f"🕐 *Время:* {time}\n"
            f"💰 *Стоимость:* {price}₽",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_booking")],
                [InlineKeyboardButton("❌ Отмена", callback_data="back_to_main")]
            ])
        )

    elif data == "confirm_booking":
        required = ['service', 'date', 'time', 'price', 'duration']
        if not all(k in context.user_data for k in required):
            await safe_edit_message(query, "Сессия устарела. Начните заново.", user_main_menu())
            return
        
        service = context.user_data['service']
        date = context.user_data['date']
        time = context.user_data['time']
        price = context.user_data['price']
        duration = context.user_data['duration']
        
        if time not in get_available_times(date, duration):
            await safe_edit_message(query, "К сожалению, это время уже занято. Попробуйте снова.", user_main_menu())
            return
        
        user = get_user(user_id)
        if not user:
            await safe_edit_message(query, "Ошибка: пользователь не найден.", user_main_menu())
            return
        
        full_name, phone = user
        
        try:
            add_booking(user_id, service, date, time, price)
            
            # Отправляем уведомление админам
            booking_details = (service, date, time, price)
            user_info = (full_name, phone)
            await notify_admins_about_booking(booking_details, user_info)
            
            context.user_data.clear()
            await safe_edit_message(
                query, 
                "✅ *Запись успешно подтверждена!*\n\nМы ждем вас в указанное время.", 
                reply_markup=user_main_menu(),
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Ошибка при создании записи: {e}")
            await safe_edit_message(
                query, 
                "❌ Не удалось создать запись. Попробуйте позже.", 
                reply_markup=user_main_menu()
            )

    # === ОБРАБОТЧИКИ ДЛЯ АДМИН-МЕНЮ ===
    
    # АДМИН-МЕНЮ
    elif data == "admin_menu" or (is_admin and data == "back_to_main"):
        await safe_edit_message(query, "🛠 Админ-панель:", reply_markup=admin_main_menu())

    # 1. Мои услуги
    elif data == "admin_services":
        services = get_services()
        if not services:
            text = "📭 Нет услуг."
        else:
            text = "💅 *Мои услуги:*\n\n"
            for name, price, duration in services:
                text += f"• *{name}* — {price}₽ ({duration} мин)\n"
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=admin_services_menu()
        )

    elif data == "admin_add_service":
        await query.edit_message_text(
            "Введите данные услуги в формате:\n*Название, цена, длительность (мин)*\nПример: Стрижка, 1500, 60",
            parse_mode='Markdown',
            reply_markup=back_to_admin()
        )
        context.user_data['awaiting'] = 'add_service'

    elif data == "admin_del_service":
        services = get_services()
        if not services:
            await safe_edit_message(query, "📭 Нет услуг.", reply_markup=admin_services_menu())
        else:
            await query.edit_message_text(
                "Выберите услугу для удаления:",
                reply_markup=delete_service_menu(services)
            )

    elif data.startswith("del_service:"):
        service_name = data.split(":", 1)[1]
        delete_service(service_name)
        await safe_edit_message(query, f"✅ Услуга '{service_name}' удалена.", reply_markup=admin_services_menu())

    # 2. Календарь
    elif data == "admin_view_calendar":
        today = datetime.today()
        await query.edit_message_text(
            "📅 *Календарь записей:*",
            parse_mode='Markdown',
            reply_markup=generate_calendar(today.year, today.month)
        )

    elif data.startswith("calendar_nav:"):
        parts = data.split(":")
        if len(parts) != 3:
            return
        year = int(parts[1])
        month = int(parts[2])
        await query.edit_message_text(
            "📅 *Календарь записей:*",
            parse_mode='Markdown',
            reply_markup=generate_calendar(year, month)
        )

    elif data.startswith("calendar_select:"):
        date = data.split(":", 1)[1]
        with closing(sqlite3.connect('bot.db')) as conn:
            bookings = conn.execute("""
                SELECT b.id, b.user_id, b.service, b.time, b.price, u.full_name, u.phone
                FROM bookings b
                LEFT JOIN users u ON b.user_id = u.user_id
                WHERE b.date = ?
                ORDER BY b.time
            """, (date,)).fetchall()
        
        keyboard_buttons = []
        
        if not bookings:
            text = f"📅 *{date}*\n\n📭 Нет записей на эту дату."
        else:
            text = f"📅 *{date}*\n\n*Записи:*\n"
            for b in bookings:
                text += f"• *{b[5] or f'Клиент ID:{b[1]}'}* - {b[2]} в {b[3]} ({b[4]}₽)\n"
                text += f"  📞 Телефон: `{b[6] or 'Нет'}`\n"
                text += f"  🆔 ID записи: `{b[0]}`\n"
                text += "  ――――――――――――――――――\n"
                
                # Добавляем кнопку для отмены записи (только для админов)
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        f"❌ Отменить запись #{b[0]}", 
                        callback_data=f"admin_cancel_booking:{b[0]}"
                    )
                ])
        
        # Добавляем кнопки навигации
        keyboard_buttons.append([
            InlineKeyboardButton("⬅️ Назад к календарю", callback_data="admin_view_calendar")
        ])
        keyboard_buttons.append([
            InlineKeyboardButton("⬅️ В меню", callback_data="admin_menu")
        ])
        
        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard_buttons)
        )

    elif data.startswith("admin_cancel_booking:"):
        # Проверяем, что пользователь - админ
        if user_id not in ADMINS:
            await safe_edit_message(query, "🚫 Доступ запрещён.", user_main_menu())
            return
            
        booking_id = int(data.split(":", 1)[1])
        
        # Получаем запись из базы
        booking = get_booking_by_id(booking_id)
        if not booking:
            await safe_edit_message(query, "❌ Запись не найдена.", admin_main_menu())
            return
        
        # Распаковываем данные записи
        booking_id, booking_user_id, service, date, time, price = booking
        
        # Получаем информацию о пользователе
        user = get_user_by_id(booking_user_id)
        user_info = None
        booking_details = None
        
        if user:
            full_name, phone = user
            user_info = (full_name, phone)
            booking_details = (service, date, time, price)
        
        # Удаляем запись
        delete_booking(booking_id)
        
        # Отправляем уведомление всем админам об отмене АДМИНОМ
        if user_info and booking_details:
            await notify_admins_about_cancellation(booking_details, user_info, cancelled_by_admin=True)
        
        # Показываем подтверждение
        if user_info:
            await safe_edit_message(
                query, 
                f"✅ Запись #{booking_id} ({service} на {date} в {time}) отменена.\n"
                f"Клиент: {user_info[0]}", 
                admin_main_menu()
            )
        else:
            await safe_edit_message(
                query, 
                f"✅ Запись #{booking_id} отменена.", 
                admin_main_menu()
            )

    # 3. Закрыть время
    elif data == "admin_close_slots":
        await safe_edit_message(query, "🚫 *Закрытие времени:*", parse_mode='Markdown', reply_markup=admin_close_slots_menu())

    elif data == "close_day":
        # Только для закрытия всего дня
        await safe_edit_message(query, 
            "📅 *Выберите день для закрытия:*\n\n🚫 — понедельники (уже закрыты)", 
            parse_mode='Markdown', 
            reply_markup=date_picker()
        )
        context.user_data['close_mode'] = 'day'

    elif data == "close_time":
        # Для закрытия конкретного времени
        await query.edit_message_text(
            "Выберите дату для закрытия времени:",
            reply_markup=date_picker()
        )
        context.user_data['close_mode'] = 'time'

    elif data.startswith("select_date_for_close:"):
        date = data.split(":", 1)[1]
        
        if context.user_data.get('close_mode') == 'day':
            # Закрыть весь день
            close_day(date)
            await safe_edit_message(query, f"✅ День *{date}* закрыт.", 
                                   parse_mode='Markdown', 
                                   reply_markup=admin_close_slots_menu())
            context.user_data.pop('close_mode', None)
            
        elif context.user_data.get('close_mode') == 'time':
            # Закрыть конкретное время - переходим к выбору времени
            context.user_data['close_time_date'] = date
            await safe_edit_message(query, 
                f"*Дата:* {date}\nВыберите время для закрытия:", 
                parse_mode='Markdown', 
                reply_markup=time_picker()
            )

    elif data.startswith("select_time_for_close:"):
        time = data.split(":", 1)[1]
        date = context.user_data.get('close_time_date')
        if date:
            close_time(date, time)
            context.user_data.pop('close_time_date', None)
            context.user_data.pop('close_mode', None)
            await safe_edit_message(query, 
                f"✅ Время *{time}* в *{date}* закрыто.", 
                parse_mode='Markdown', 
                reply_markup=admin_close_slots_menu()
            )

    elif data == "open_slots":
        closed = get_closed_slots()
        if not closed:
            await safe_edit_message(query, "📭 Нет закрытых дней или времени.", parse_mode='Markdown', reply_markup=admin_close_slots_menu())
            return
        
        await query.edit_message_text(
            "Выберите слот для открытия:",
            reply_markup=open_slots_menu(closed)
        )

    elif data.startswith("open_slot:"):
        parts = data.split(":")
        if len(parts) != 3:
            return
        
        date = parts[1]
        time_or_all = parts[2]
        
        if time_or_all == "all":
            open_day(date)
            await safe_edit_message(
                query, 
                f"✅ День *{date}* открыт.", 
                parse_mode='Markdown', 
                reply_markup=admin_close_slots_menu()
            )
        else:
            # Открываем конкретное время
            time = time_or_all
            open_time(date, time)
            await safe_edit_message(
                query, 
                f"✅ Время *{time}* в *{date}* открыто.", 
                parse_mode='Markdown', 
                reply_markup=admin_close_slots_menu()
            )

    # 4. График работы
    elif data == "admin_working_hours":
        start, end = get_working_hours()
        await safe_edit_message(
            query,
            f"🕒 *Текущее время работы:*\n*С {start} до {end}*\n\n*Выходной:* Понедельник",
            parse_mode='Markdown',
            reply_markup=admin_working_hours_menu()
        )

    elif data == "edit_working_hours":
        await query.edit_message_text(
            "Введите новое время работы в формате:\n*Начало, Конец*\nПример: 09:00, 19:00",
            parse_mode='Markdown',
            reply_markup=back_to_admin()
        )
        context.user_data['awaiting'] = 'set_working_hours'

    else:
        menu = admin_main_menu() if is_admin else user_main_menu()
        await safe_edit_message(query, "Неизвестная команда.", menu)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    await update.message.reply_text("🛠 Админ-панель:", reply_markup=admin_main_menu())

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            await update.message.reply_text(f"✅ Услуга '{name}' добавлена.", reply_markup=admin_services_menu())
        except:
            await update.message.reply_text("❌ Формат: Название, цена, длительность", reply_markup=back_to_admin())
        context.user_data['awaiting'] = None

    elif state == 'set_working_hours':
        try:
            parts = text.split(',')
            if len(parts) != 2:
                raise ValueError
            start = parse_time(parts[0].strip())
            end = parse_time(parts[1].strip())
            datetime.strptime(start, "%H:%M")
            datetime.strptime(end, "%H:%M")
            if start >= end:
                raise ValueError
            set_working_hours(start, end)
            await update.message.reply_text(
                f"✅ Время работы установлено: {start}–{end}",
                reply_markup=admin_working_hours_menu()
            )
        except Exception as e:
            print("Ошибка при установке времени:", e)
            await update.message.reply_text("❌ Формат: 09:00, 19:00", reply_markup=back_to_admin())
        context.user_data['awaiting'] = None

    else:
        await update.message.reply_text("Неизвестная команда.", reply_markup=admin_main_menu())
