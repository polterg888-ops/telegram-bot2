# database.py
import sqlite3
from contextlib import closing

def init_db():
    with closing(sqlite3.connect('bot.db')) as conn:
        # Создаем все таблицы сначала
        conn.execute("""
            CREATE TABLE IF NOT EXISTS barber (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name TEXT DEFAULT 'Дмитрий',
                phone TEXT DEFAULT '+79991234567'
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS services (
                name TEXT PRIMARY KEY,
                price INTEGER,
                duration INTEGER
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                service TEXT,
                date TEXT,
                time TEXT,
                price INTEGER
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS closed_slots (
                date TEXT,
                time TEXT,
                PRIMARY KEY (date, time)
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS working_hours (
                start_time TEXT DEFAULT '09:00',
                end_time TEXT DEFAULT '19:00'
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                phone TEXT
            )
        """)
        
        conn.commit()  # Коммитим создание таблиц
        
        # Инициализируем мастера, если его нет
        conn.execute("INSERT OR IGNORE INTO barber (id, name, phone) VALUES (1, 'Мастер', '+7 951 765 9053')")
        
        # Инициализируем рабочее время
        conn.execute("INSERT OR IGNORE INTO working_hours (start_time, end_time) VALUES ('09:00', '19:00')")
        
        # Добавляем начальные услуги если их нет
        initial_services = [
            ('Мужская стрижка', 899, 60),
            ('Детская стрижка', 799, 60),
            ('Стрижка бороды', 699, 60)
        ]
        
        for name, price, duration in initial_services:
            conn.execute("INSERT OR IGNORE INTO services (name, price, duration) VALUES (?, ?, ?)",
                        (name, price, duration))
        
        conn.commit()

# === Мастер ===
def get_barber():
    with closing(sqlite3.connect('bot.db')) as conn:
        return conn.execute("SELECT name, phone FROM barber WHERE id = 1").fetchone()

def update_barber(name, phone):
    with closing(sqlite3.connect('bot.db')) as conn:
        conn.execute("UPDATE barber SET name = ?, phone = ? WHERE id = 1", (name, phone))
        conn.commit()

def get_barber_name():
    with closing(sqlite3.connect('bot.db')) as conn:
        row = conn.execute("SELECT name FROM barber WHERE id = 1").fetchone()
        return row[0] if row else 'Мастер'


# === Услуги ===
def add_service(name, price, duration):
    with closing(sqlite3.connect('bot.db')) as conn:
        conn.execute("INSERT OR REPLACE INTO services (name, price, duration) VALUES (?, ?, ?)",
                     (name, price, duration))
        conn.commit()

def delete_service(name):
    with closing(sqlite3.connect('bot.db')) as conn:
        conn.execute("DELETE FROM services WHERE name = ?", (name,))
        conn.commit()

def get_services():
    with closing(sqlite3.connect('bot.db')) as conn:
        return conn.execute("SELECT name, price, duration FROM services ORDER BY name").fetchall()


# === Записи ===
def add_booking(user_id, service, date, time, price):
    with closing(sqlite3.connect('bot.db')) as conn:
        conn.execute("""
            INSERT INTO bookings (user_id, service, date, time, price)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, service, date, time, price))
        conn.commit()

def get_user_bookings(user_id):
    with closing(sqlite3.connect('bot.db')) as conn:
        return conn.execute("""
            SELECT id, service, date, time, price
            FROM bookings
            WHERE user_id = ?
            ORDER BY date DESC, time DESC
        """, (user_id,)).fetchall()

def get_all_bookings():
    with closing(sqlite3.connect('bot.db')) as conn:
        return conn.execute("""
            SELECT id, user_id, service, date, time, price
            FROM bookings
            ORDER BY date DESC, time DESC
        """).fetchall()

def get_booking_by_id_and_user(booking_id, user_id):
    with closing(sqlite3.connect('bot.db')) as conn:
        row = conn.execute("""
            SELECT service, date, time, price
            FROM bookings
            WHERE id = ? AND user_id = ?
        """, (booking_id, user_id)).fetchone()
        return row

def get_booking_by_id(booking_id):
    with closing(sqlite3.connect('bot.db')) as conn:
        row = conn.execute("""
            SELECT id, user_id, service, date, time, price
            FROM bookings WHERE id = ?
        """, (booking_id,)).fetchone()
        return row

def delete_booking(booking_id):
    with closing(sqlite3.connect('bot.db')) as conn:
        conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        conn.commit()


# === Время работы ===
def set_working_hours(start, end):
    with closing(sqlite3.connect('bot.db')) as conn:
        conn.execute("UPDATE working_hours SET start_time = ?, end_time = ?", (start, end))
        conn.commit()

def get_working_hours():
    with closing(sqlite3.connect('bot.db')) as conn:
        row = conn.execute("SELECT start_time, end_time FROM working_hours").fetchone()
        if row:
            return row[0], row[1]
        else:
            return "09:00", "19:00"


# === Закрытые слоты ===
def close_day(date):
    with closing(sqlite3.connect('bot.db')) as conn:
        conn.execute("INSERT OR IGNORE INTO closed_slots (date, time) VALUES (?, NULL)", (date,))
        conn.commit()

def close_time(date, time):
    with closing(sqlite3.connect('bot.db')) as conn:
        conn.execute("INSERT OR IGNORE INTO closed_slots (date, time) VALUES (?, ?)", (date, time))
        conn.commit()

def open_day(date):
    with closing(sqlite3.connect('bot.db')) as conn:
        conn.execute("DELETE FROM closed_slots WHERE date = ? AND time IS NULL", (date,))
        conn.commit()

def open_time(date, time):
    with closing(sqlite3.connect('bot.db')) as conn:
        conn.execute("DELETE FROM closed_slots WHERE date = ? AND time = ?", (date, time))
        conn.commit()

def is_closed(date, time):
    with closing(sqlite3.connect('bot.db')) as conn:
        # Закрыт ли весь день?
        row = conn.execute("SELECT 1 FROM closed_slots WHERE date = ? AND time IS NULL", (date,)).fetchone()
        if row:
            return True
        # Закрыто ли конкретное время?
        if time:
            row = conn.execute("SELECT 1 FROM closed_slots WHERE date = ? AND time = ?", (date, time)).fetchone()
            return bool(row)
        return False

def get_closed_slots():
    with closing(sqlite3.connect('bot.db')) as conn:
        return conn.execute("SELECT date, time FROM closed_slots ORDER BY date, time").fetchall()


# === Пользователи ===
def save_user(user_id, full_name, phone):
    with closing(sqlite3.connect('bot.db')) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO users (user_id, full_name, phone)
            VALUES (?, ?, ?)
        """, (user_id, full_name, phone))
        conn.commit()

def get_user(user_id):
    with closing(sqlite3.connect('bot.db')) as conn:
        row = conn.execute("SELECT full_name, phone FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return row

def get_user_by_id(user_id):
    """Получить пользователя по ID"""
    with closing(sqlite3.connect('bot.db')) as conn:
        row = conn.execute("SELECT full_name, phone FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            return row
        return None