"""
Модель бронирования для системы бронирования ресторана.

Класс Booking инкапсулирует:
  - SQL-схема таблицы bookings
  - Константы имён колонок
  - Внешние связи с таблицами users и tables
  - CRUD-операции через DatabaseDriver
"""

from datetime import datetime
from typing import Optional

from db_driver.driver import DatabaseDriver

# --------------------------------------------------------------- #
# Имена колонок и схема таблицы
# --------------------------------------------------------------- #

TABLE_NAME = "bookings"

SCHEMA: dict[str, str] = {
    "id": "SERIAL PRIMARY KEY",
    "user_id": "INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE",
    "table_id": "INTEGER NOT NULL REFERENCES tables(id) ON DELETE CASCADE",
    "start_time": "TIMESTAMP NOT NULL",
    "end_time": "TIMESTAMP NOT NULL",
    "guests_count": "INTEGER NOT NULL CHECK (guests_count > 0)",
    "status": "VARCHAR(20) DEFAULT 'confirmed'",
    "notes": "TEXT",
    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
}

# --------------------------------------------------------------- #
# Статусы бронирования
# --------------------------------------------------------------- #

STATUS_CONFIRMED = "confirmed"
STATUS_CANCELLED = "cancelled"
STATUS_COMPLETED = "completed"
STATUS_NO_SHOW = "no_show"

VALID_STATUSES = {STATUS_CONFIRMED, STATUS_CANCELLED, STATUS_COMPLETED, STATUS_NO_SHOW}

# --------------------------------------------------------------- #
# Класс Booking
# --------------------------------------------------------------- #

class Booking:
    """Модель бронирования ресторана."""

    TABLE_NAME = "bookings"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_COMPLETED = "completed"
    STATUS_NO_SHOW = "no_show"

    # ----------------------------------------------------------- #
    # Создание таблицы
    # ----------------------------------------------------------- #

    @staticmethod
    def create_table(driver: DatabaseDriver) -> bool:
        """Создаёт таблицу bookings в базе данных."""
        return driver.create_table(TABLE_NAME, SCHEMA)

    # ----------------------------------------------------------- #
    # Создание бронирования
    # ----------------------------------------------------------- #

    @staticmethod
    def insert(
        driver: DatabaseDriver,
        user_id: int,
        table_id: int,
        start_time: datetime,
        end_time: datetime,
        guests_count: int,
        status: str = STATUS_CONFIRMED,
        notes: Optional[str] = None,
    ) -> Optional[int]:
        """
        Создаёт новое бронирование.

        Параметры:
            user_id:      ID пользователя, который бронирует.
            table_id:     ID стола, который бронируется.
            start_time:   Время начала бронирования.
            end_time:     Время окончания бронирования.
            guests_count: Количество гостей.
            status:       Статус бронирования (по умолчанию 'confirmed').
            notes:        Заметки к бронированию (опционально).

        Возвращает:
            ID созданной записи или None в случае ошибки.
        """
        if start_time >= end_time:
            raise ValueError("Время окончания должно быть позже времени начала.")
        if status not in VALID_STATUSES:
            raise ValueError(f"Недопустимый статус: {status}")
        if guests_count <= 0:
            raise ValueError("Количество гостей должно быть больше нуля.")

        now = datetime.now()
        data = {
            "user_id": user_id,
            "table_id": table_id,
            "start_time": start_time,
            "end_time": end_time,
            "guests_count": guests_count,
            "status": status,
            "notes": notes,
            "created_at": now,
            "updated_at": now,
        }
        return driver.insert(TABLE_NAME, data, return_id=True)

    # ----------------------------------------------------------- #
    # Поиск бронирований
    # ----------------------------------------------------------- #

    @staticmethod
    def select_by_id(driver: DatabaseDriver, booking_id: int) -> Optional[tuple]:
        """Возвращает запись бронирования по ID."""
        return driver.select_by_id(TABLE_NAME, booking_id)

    @staticmethod
    def select_by_user(driver: DatabaseDriver, user_id: int) -> list[tuple]:
        """Возвращает все бронирования пользователя."""
        rows = driver.select_by_field(TABLE_NAME, "user_id", user_id)
        return rows

    @staticmethod
    def select_by_table(driver: DatabaseDriver, table_id: int) -> list[tuple]:
        """Возвращает все бронирования для указанного стола."""
        rows = driver.select_by_field(TABLE_NAME, "table_id", table_id)
        return rows

    @staticmethod
    def select_active(driver: DatabaseDriver) -> list[tuple]:
        """Возвращает все активные (подтверждённые) бронирования."""
        query = f"SELECT * FROM {TABLE_NAME} WHERE status = '{STATUS_CONFIRMED}' ORDER BY start_time;"
        with driver._cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    @staticmethod
    def select_by_date(
        driver: DatabaseDriver,
        date: datetime,
        status: Optional[str] = None,
    ) -> list[tuple]:
        """
        Возвращает бронирования на указанную дату.

        Параметры:
            date:   Дата для поиска.
            status: Опциональный фильтр по статусу.
        """
        day_start = datetime(date.year, date.month, date.day)
        day_end = day_start.replace(hour=23, minute=59, second=59)

        query = (
            f"SELECT * FROM {TABLE_NAME} "
            f"WHERE start_time >= %s AND start_time <= %s"
        )
        params: list = [day_start, day_end]

        if status:
            if status not in VALID_STATUSES:
                raise ValueError(f"Недопустимый статус: {status}")
            query += f" AND status = %s"
            params.append(status)

        query += " ORDER BY start_time;"

        with driver._cursor() as cursor:
            cursor.execute(query, tuple(params))
            return cursor.fetchall()

    # ----------------------------------------------------------- #
    # Обновление
    # ----------------------------------------------------------- #

    @staticmethod
    def update(
        driver: DatabaseDriver,
        booking_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        status: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """
        Обновляет данные бронирования.

        Возвращает:
            True при успешном обновлении, False — в случае ошибки.
        """
        if status is not None and status not in VALID_STATUSES:
            raise ValueError(f"Недопустимый статус: {status}")

        data = {"updated_at": datetime.now()}
        if start_time is not None:
            data["start_time"] = start_time
        if end_time is not None:
            data["end_time"] = end_time
        if status is not None:
            data["status"] = status
        if notes is not None:
            data["notes"] = notes

        updated = driver.update(TABLE_NAME, data, {"id": booking_id})
        return updated > 0

    @staticmethod
    def cancel(driver: DatabaseDriver, booking_id: int) -> bool:
        """Отменяет бронирование."""
        data = {"status": STATUS_CANCELLED, "updated_at": datetime.now()}
        updated = driver.update(TABLE_NAME, data, {"id": booking_id})
        return updated > 0

    @staticmethod
    def complete(driver: DatabaseDriver, booking_id: int) -> bool:
        """Завершает бронирование (гость посетил ресторан)."""
        data = {"status": STATUS_COMPLETED, "updated_at": datetime.now()}
        updated = driver.update(TABLE_NAME, data, {"id": booking_id})
        return updated > 0

    @staticmethod
    def cancel_conflicting(
        driver: DatabaseDriver,
        table_id: int,
        start_time: datetime,
        end_time: datetime,
    ) -> list[int]:
        """
        Отменяет все конфликтующие бронирования для стола в указанный период.

        Возвращает:
            Список ID отменённых бронирований.
        """
        query = (
            f"UPDATE {TABLE_NAME} "
            f"SET status = '{STATUS_CANCELLED}', updated_at = %s "
            f"WHERE table_id = %s "
            f"AND status = '{STATUS_CONFIRMED}' "
            f"AND start_time < %s "
            f"AND end_time > %s "
            f"RETURNING id;"
        )

        cancelled_ids: list[int] = []
        with driver._cursor(commit=True) as cursor:
            cursor.execute(query, (datetime.now(), table_id, end_time, start_time))
            rows = cursor.fetchall()
            for row in rows:
                cancelled_ids.append(row[0])

        return cancelled_ids

    # ----------------------------------------------------------- #
    # Проверка существования
    # ----------------------------------------------------------- #

    @staticmethod
    def exists(
        driver: DatabaseDriver,
        booking_id: Optional[int] = None,
        table_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
    ) -> bool:
        """
        Проверяет существование бронирования по ID, столу и/или времени.

        Возвращает:
            True, если бронирование найдено.
        """
        if booking_id:
            if driver.exists(TABLE_NAME, "id", booking_id):
                return True
        if table_id and start_time:
            # Проверяем коллизию: есть ли бронирование для стола в это время
            query = (
                f"SELECT EXISTS("
                f"SELECT 1 FROM {TABLE_NAME} "
                f"WHERE table_id = %s "
                f"AND start_time < %s "
                f"AND end_time > %s"
                f")"
            )
            with driver._cursor() as cursor:
                cursor.execute(query, (table_id, start_time, start_time))
                result = cursor.fetchone()
                return bool(result[0]) if result else False
        return False
