"""
Backend для создания таблиц системы бронирования.

Содержит CRUD-функции для таблиц users, tables и bookings.
"""

from datetime import datetime
from typing import Optional

from db_driver.driver import DatabaseDriver
from models.user import User
from models.table import Table
from models.booking import Booking, STATUS_CONFIRMED


# =============================================================== #
# Инициализация
# =============================================================== #

def init_db():
    """Инициализация базы данных — создание таблиц."""
    driver = DatabaseDriver()
    driver.connect()

    try:
        User.create_table(driver)
        print("Таблица users создана.")

        Table.create_table(driver)
        print("Таблица tables создана.")

        Booking.create_table(driver)
        print("Таблица bookings создана.")
    finally:
        driver.close()


# =============================================================== #
# USERS — CRUD
# =============================================================== #

def create_user(
    driver: DatabaseDriver,
    username: str,
    email: str,
    full_name: Optional[str] = None,
    phone: Optional[str] = None,
) -> Optional[int]:
    """Создаёт нового пользователя."""
    return User.insert(driver, username, email, full_name, phone)


def read_user(driver: DatabaseDriver, user_id: int) -> Optional[tuple]:
    """Читает пользователя по ID."""
    return User.select_by_id(driver, user_id)


def read_users_by_username(driver: DatabaseDriver, username: str) -> Optional[tuple]:
    """Читает пользователя по имени."""
    return User.select_by_username(driver, username)


def read_users_by_email(driver: DatabaseDriver, email: str) -> Optional[tuple]:
    """Читает пользователя по email."""
    return User.select_by_email(driver, email)


def read_all_active_users(driver: DatabaseDriver) -> list[tuple]:
    """Читает всех активных пользователей."""
    return User.select_all_active(driver)


def update_user(
    driver: DatabaseDriver,
    user_id: int,
    full_name: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
) -> bool:
    """Обновляет данные пользователя."""
    return User.update(driver, user_id, full_name, phone, email)


def delete_user(driver: DatabaseDriver, user_id: int) -> bool:
    """Удаляет пользователя (soft delete — деактивация)."""
    return User.deactivate(driver, user_id)


# =============================================================== #
# TABLES — CRUD
# =============================================================== #

def create_table(
    driver: DatabaseDriver,
    table_number: str,
    seats: int,
    zone: Optional[str] = None,
) -> Optional[int]:
    """Создаёт новый стол."""
    return Table.insert(driver, table_number, seats, zone)


def read_table(driver: DatabaseDriver, table_id: int) -> Optional[tuple]:
    """Читает стол по ID."""
    return Table.select_by_id(driver, table_id)


def read_table_by_number(driver: DatabaseDriver, table_number: str) -> Optional[tuple]:
    """Читает стол по номеру."""
    return Table.select_by_number(driver, table_number)


def read_all_active_tables(driver: DatabaseDriver) -> list[tuple]:
    """Читает все активные столы."""
    return Table.select_all_active(driver)


def read_tables_by_seats(
    driver: DatabaseDriver,
    min_seats: int,
    max_seats: Optional[int] = None,
) -> list[tuple]:
    """Читает столы по количеству мест."""
    return Table.select_by_seats(driver, min_seats, max_seats)


def update_table(
    driver: DatabaseDriver,
    table_id: int,
    table_number: Optional[str] = None,
    seats: Optional[int] = None,
    zone: Optional[str] = None,
) -> bool:
    """Обновляет данные стола."""
    return Table.update(driver, table_id, table_number, seats, zone)


def delete_table(driver: DatabaseDriver, table_id: int) -> bool:
    """Удаляет стол (soft delete — деактивация)."""
    return Table.deactivate(driver, table_id)


# =============================================================== #
# BOOKINGS — CRUD
# =============================================================== #

def create_booking(
    driver: DatabaseDriver,
    user_id: int,
    table_id: int,
    start_time: datetime,
    end_time: datetime,
    guests_count: int,
    status: str = STATUS_CONFIRMED,
    notes: Optional[str] = None,
) -> Optional[int]:
    """Создаёт новое бронирование."""
    return Booking.insert(driver, user_id, table_id, start_time, end_time, guests_count, status, notes)


def read_booking(driver: DatabaseDriver, booking_id: int) -> Optional[tuple]:
    """Читает бронирование по ID."""
    return Booking.select_by_id(driver, booking_id)


def read_bookings_by_user(driver: DatabaseDriver, user_id: int) -> list[tuple]:
    """Читает все бронирования пользователя."""
    return Booking.select_by_user(driver, user_id)


def read_bookings_by_table(driver: DatabaseDriver, table_id: int) -> list[tuple]:
    """Читает все бронирования стола."""
    return Booking.select_by_table(driver, table_id)


def read_active_bookings(driver: DatabaseDriver) -> list[tuple]:
    """Читает все активные (подтверждённые) бронирования."""
    return Booking.select_active(driver)


def read_bookings_by_date(
    driver: DatabaseDriver,
    date: datetime,
    status: Optional[str] = None,
) -> list[tuple]:
    """Читает бронирования на указанную дату."""
    return Booking.select_by_date(driver, date, status)


def update_booking(
    driver: DatabaseDriver,
    booking_id: int,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    status: Optional[str] = None,
    notes: Optional[str] = None,
) -> bool:
    """Обновляет данные бронирования."""
    return Booking.update(driver, booking_id, start_time, end_time, status, notes)


def delete_booking(driver: DatabaseDriver, booking_id: int) -> bool:
    """Удаляет бронирование (soft delete — отмена)."""
    return Booking.cancel(driver, booking_id)


def check_table_availability(
    driver: DatabaseDriver,
    table_id: int,
    start_time: datetime,
    end_time: datetime,
) -> tuple[bool, list[tuple]]:
    """
    Проверяет доступность стола в указанный временной диапазон.

    Возвращает:
        (True, []) — стол свободен
        (False, [conflicting_bookings]) — стол занят, возвращает конфликтующие бронирования
        
    Каждая строка conflicts: (id, user_id, table_id, start_time,
                             end_time, guests_count, status, notes,
                             created_at, updated_at)
    """
    if start_time >= end_time:
        return False, []

    query = f"""
        SELECT id, user_id, table_id, start_time, end_time, guests_count, status, notes, created_at, updated_at
        FROM {Booking.TABLE_NAME}
        WHERE table_id = %s
          AND status = '{Booking.STATUS_CONFIRMED}'
          AND start_time < %s
          AND end_time > %s
        ORDER BY start_time;
    """

    try:
        with driver._cursor() as cursor:
            cursor.execute(query, (table_id, end_time, start_time))
            conflicts = cursor.fetchall()

        if conflicts:
            return False, conflicts
        return True, []
    except Exception:
        return False, []

    query = f"""
        SELECT id, user_id, table_id, booked_at, start_time, end_time,
               guests_count, status, notes, created_at, updated_at
        FROM {Booking.TABLE_NAME}
        WHERE table_id = %s
          AND status = '{Booking.STATUS_CONFIRMED}'
          AND start_time < %s
          AND end_time > %s
        ORDER BY start_time;
    """

    try:
        with driver._cursor() as cursor:
            cursor.execute(query, (table_id, end_time, start_time))
            conflicts = cursor.fetchall()

        if conflicts:
            return False, conflicts
        return True, []
    except Exception:
        return False, []


# =============================================================== #
# Пример использования
# =============================================================== #

if __name__ == "__main__":
    db = DatabaseDriver()
    db.connect()

    try:
        # 1. Создаём таблицы
        init_db()

        # 2. Создаём пользователя
        user_id = create_user(db, "ivan", "ivan@example.com", "Иван Петров", "+7-900-123-45-67")
        print(f"Создан пользователь, ID: {user_id}")

        # 3. Читаем пользователя
        user = read_user(db, user_id)
        print(f"Пользователь: {user}")

        # 4. Создаём стол
        table_id = create_table(db, "A1", 4, "Основной зал")
        print(f"Создан стол, ID: {table_id}")

        # 5. Читаем стол
        table = read_table(db, table_id)
        print(f"Стол: {table}")

        # 6. Создаём бронирование
        start = datetime(2026, 1, 15, 19, 0)
        end = datetime(2026, 1, 15, 21, 0)
        booking_id = create_booking(db, user_id, table_id, start, end, 3, "Юбилей")
        print(f"Создано бронирование, ID: {booking_id}")

        # 7. Читаем бронирование
        booking = read_booking(db, booking_id)
        print(f"Бронирование: {booking}")

        # 8. Обновляем пользователя
        update_user(db, user_id, full_name="Иван Иванович")
        print("Пользователь обновлён.")

        # 9. Читаем все активные столы
        tables = read_all_active_tables(db)
        print(f"Активные столы: {len(tables)}")

        # 10. Читаем бронирования на дату
        bookings = read_bookings_by_date(db, datetime(2026, 1, 15))
        print(f"Бронирования на 15.01.2026: {len(bookings)}")

        # 11. Удаляем (деактивируем) пользователя
        delete_user(db, user_id)
        print("Пользователь деактивирован.")

    finally:
        db.close()
