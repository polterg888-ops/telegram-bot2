# bot/admin_keyboards.py
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

def admin_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1️⃣ Мои услуги", callback_data="admin_services")],
        [InlineKeyboardButton("2️⃣ Календарь", callback_data="admin_view_calendar")],
        [InlineKeyboardButton("3️⃣ Закрыть время", callback_data="admin_close_slots")],
        [InlineKeyboardButton("4️⃣ График работы", callback_data="admin_working_hours")]
    ])

def admin_services_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить услугу", callback_data="admin_add_service")],
        [InlineKeyboardButton("🗑 Удалить услугу", callback_data="admin_del_service")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_menu")]
    ])

def admin_working_hours_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Изменить время", callback_data="edit_working_hours")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_menu")]
    ])

def admin_close_slots_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Закрыть день", callback_data="close_day")],
        [InlineKeyboardButton("⏱ Закрыть время", callback_data="close_time")],
        [InlineKeyboardButton("🔓 Открыть слоты", callback_data="open_slots")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_menu")]
    ])

def generate_calendar(year=None, month=None):
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
        InlineKeyboardButton("⬅️", callback_data=f"calendar_nav:{prev_year}:{prev_month}"),
        InlineKeyboardButton(f"{month_names[month-1]} {year}", callback_data="ignore"),
        InlineKeyboardButton("➡️", callback_data=f"calendar_nav:{next_year}:{next_month}")
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
        
        if date_obj < today.date():
            day_buttons.append(InlineKeyboardButton(f"❌{day}", callback_data="ignore"))
        else:
            day_buttons.append(InlineKeyboardButton(f"{day}", callback_data=f"calendar_select:{date_str}"))
        
        if len(day_buttons) == 7:
            buttons.append(day_buttons)
            day_buttons = []
    
    while len(day_buttons) < 7:
        day_buttons.append(InlineKeyboardButton(" ", callback_data="ignore"))
    if day_buttons:
        buttons.append(day_buttons)
    
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_menu")])
    
    return InlineKeyboardMarkup(buttons)

def date_picker():
    from datetime import datetime, timedelta
    today = datetime.today().date()
    dates = []
    for i in range(30):
        d = today + timedelta(days=i)
        dates.append(d.strftime("%Y-%m-%d"))
    
    buttons = []
    row = []
    for d in dates:
        date_obj = datetime.strptime(d, "%Y-%m-%d").date()
        weekday = date_obj.weekday()
        
        # Отмечаем понедельники как нерабочие
        if weekday == 0:
            label = f"🚫 {d[5:]}"
        else:
            label = d[5:]
            
        row.append(InlineKeyboardButton(label, callback_data=f"select_date_for_close:{d}"))
        if len(row) == 7:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_close_slots")])
    return InlineKeyboardMarkup(buttons)

def time_picker():
    from datetime import datetime
    import sqlite3
    from contextlib import closing
    
    # Получаем рабочие часы из базы данных
    try:
        with closing(sqlite3.connect('bot.db')) as conn:
            row = conn.execute("SELECT start_time, end_time FROM working_hours").fetchone()
            if row:
                start_time, end_time = row
            else:
                start_time, end_time = "09:00", "19:00"
    except:
        start_time, end_time = "09:00", "19:00"
    
    # Парсим время начала и окончания
    try:
        start_hour = int(start_time.split(':')[0])
        end_hour = int(end_time.split(':')[0])
    except:
        start_hour, end_hour = 9, 19
    
    # Генерируем время в рабочих часах
    times = []
    for h in range(start_hour, end_hour):
        times.append(f"{h:02d}:00")
    
    buttons = []
    row = []
    for t in times:
        row.append(InlineKeyboardButton(f"🕐 {t}", callback_data=f"select_time_for_close:{t}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="close_time")])
    return InlineKeyboardMarkup(buttons)

def back_to_admin():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="admin_menu")]])

def delete_service_menu(services):
    buttons = []
    for name, price, duration in services:
        buttons.append([InlineKeyboardButton(f"{name} — {price}₽ ({duration} мин)", callback_data=f"del_service:{name}")])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_services")])
    return InlineKeyboardMarkup(buttons)

def open_slots_menu(closed_slots):
    buttons = []
    for date, time in closed_slots:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        weekday = date_obj.weekday()
        
        # Для понедельников показываем, что они закрыты по умолчанию
        if weekday == 0:
            continue
            
        if time is None:
            label = f"📅 {date} (весь день)"
            callback = f"open_slot:{date}:all"
        else:
            label = f"⏱ {date} {time}"
            callback = f"open_slot:{date}:{time}"
        buttons.append([InlineKeyboardButton(label, callback_data=callback)])
    
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_close_slots")])
    return InlineKeyboardMarkup(buttons)
