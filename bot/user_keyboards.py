# bot/user_keyboards.py
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

def user_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Записаться", callback_data="book")],
        [InlineKeyboardButton("📋 Мои записи", callback_data="my_bookings")]
    ])

def service_menu(services):
    buttons = []
    for name, price, duration in services:
        label = f"{name} — {price}₽ ({duration} мин)"
        buttons.append([InlineKeyboardButton(label, callback_data=f"select_service:{name}")])
    
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(buttons)

def generate_user_calendar(year=None, month=None):
    from datetime import datetime
    today = datetime.today()
    
    if year is None:
        year = today.year
    if month is None:
        month = today.month
    
    first_day = datetime(year, month, 1)
    first_weekday = first_day.weekday()
    
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    days_in_month = (next_month - first_day).days
    
    month_names = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    
    buttons = []
    
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    header = [
        InlineKeyboardButton("⬅️", callback_data=f"user_calendar_nav:{prev_year}:{prev_month}"),
        InlineKeyboardButton(f"{month_names[month-1]} {year}", callback_data="ignore"),
        InlineKeyboardButton("➡️", callback_data=f"user_calendar_nav:{next_year}:{next_month}")
    ]
    buttons.append(header)
    
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    buttons.append([InlineKeyboardButton(day, callback_data="ignore") for day in weekdays])
    
    day_buttons = []
    for _ in range(first_weekday):
        day_buttons.append(InlineKeyboardButton(" ", callback_data="ignore"))
    
    for day in range(1, days_in_month + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        date_obj = datetime(year, month, day).date()
        weekday = date_obj.weekday()
        
        if date_obj < today.date():
            day_buttons.append(InlineKeyboardButton(f"❌{day}", callback_data="ignore"))
        elif weekday == 0:
            day_buttons.append(InlineKeyboardButton(f"🚫{day}", callback_data="ignore"))
        else:
            day_buttons.append(InlineKeyboardButton(f"{day}", callback_data=f"user_calendar_select:{date_str}"))
        
        if len(day_buttons) == 7:
            buttons.append(day_buttons)
            day_buttons = []
    
    while len(day_buttons) < 7:
        day_buttons.append(InlineKeyboardButton(" ", callback_data="ignore"))
    if day_buttons:
        buttons.append(day_buttons)
    
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="book")])
    
    return InlineKeyboardMarkup(buttons)

def time_menu(times):
    buttons = []
    row = []
    
    sorted_times = sorted(times)
    
    for t in sorted_times:
        button_text = f"🕐 {t}"
        row.append(InlineKeyboardButton(button_text, callback_data=f"select_time:{t}"))
        
        if len(row) == 4:
            buttons.append(row)
            row = []
    
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("⬅️ Назад к календарю", callback_data="select_date_back")])
    
    return InlineKeyboardMarkup(buttons)

def booking_detail_menu(booking_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 Отменить запись", callback_data=f"cancel_booking:{booking_id}")],
        [InlineKeyboardButton("⬅️ Назад к записям", callback_data="my_bookings")]
    ])

def back_to_admin():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="admin_menu")]])
