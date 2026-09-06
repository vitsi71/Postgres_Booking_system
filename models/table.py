"""
Модель стола для системы бронирования ресторана.

Класс Table инкапсулирует:
  - SQL-схема таблицы tables
  - Константы имён колонок
  - CRUD-операции через DatabaseDriver
"""

from datetime import datetime
from typing import Optional

from db_driver.driver import DatabaseDriver

# --------------------------------------------------------------- #
# Имена колонок и схема таблицы
# --------------------------------------------------------------- #

TABLE_NAME = "tables"

SCHEMA: dict[str, str] = {
    "id": "SERIAL PRIMARY KEY",
    "table_number": "VARCHAR(50) UNIQUE NOT NULL",
    "seats": "INTEGER NOT NULL CHECK (seats > 0)",
    "zone": "VARCHAR(100)",
    "is_active": "BOOLEAN DEFAULT TRUE",
    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
}

# --------------------------------------------------------------- #
# Класс Table
# --------------------------------------------------------------- #

class Table:
    """Модель стола ресторана."""

    # ----------------------------------------------------------- #
    # Создание таблицы
    # ----------------------------------------------------------- #

    @staticmethod
    def create_table(driver: DatabaseDriver) -> bool:
        """Создаёт таблицу tables в базе данных."""
        return driver.create_table(TABLE_NAME, SCHEMA)

    # ----------------------------------------------------------- #
    # Создание стола
    # ----------------------------------------------------------- #

    @staticmethod
    def insert(
        driver: DatabaseDriver,
        table_number: str,
        seats: int,
        zone: Optional[str] = None,
    ) -> Optional[int]:
        """
        Создаёт новый стол.

        Параметры:
            table_number:  Уникальный номер / название стола.
            seats:         Количество посадочных мест.
            zone:          Зона ресторана (опционально).

        Возвращает:
            ID созданной записи или None в случае ошибки.
        """
        if seats <= 0:
            raise ValueError("Количество мест должно быть больше нуля.")

        now = datetime.now()
        data = {
            "table_number": table_number,
            "seats": seats,
            "zone": zone,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        return driver.insert(TABLE_NAME, data, return_id=True)

    # ----------------------------------------------------------- #
    # Поиск столов
    # ----------------------------------------------------------- #

    @staticmethod
    def select_by_id(driver: DatabaseDriver, table_id: int) -> Optional[tuple]:
        """Возвращает запись стола по ID."""
        return driver.select_by_id(TABLE_NAME, table_id)

    @staticmethod
    def select_by_number(driver: DatabaseDriver, table_number: str) -> Optional[tuple]:
        """Возвращает запись стола по номеру."""
        rows = driver.select_by_field(TABLE_NAME, "table_number", table_number)
        return rows[0] if rows else None

    @staticmethod
    def select_all_active(driver: DatabaseDriver) -> list[tuple]:
        """Возвращает все активные столы."""
        query = f"SELECT * FROM {TABLE_NAME} WHERE is_active = TRUE ORDER BY id;"
        with driver._cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    @staticmethod
    def select_by_seats(
        driver: DatabaseDriver,
        min_seats: int,
        max_seats: Optional[int] = None,
    ) -> list[tuple]:
        """
        Возвращает столы с количеством мест в диапазоне.

        Параметры:
            min_seats: Минимальное количество мест.
            max_seats: Максимальное количество мест (опционально).
        """
        if max_seats is not None:
            query = (
                f"SELECT * FROM {TABLE_NAME} "
                f"WHERE seats >= %s AND seats <= %s "
                f"AND is_active = TRUE "
                f"ORDER BY seats;"
            )
            with driver._cursor() as cursor:
                cursor.execute(query, (min_seats, max_seats))
                return cursor.fetchall()
        else:
            query = (
                f"SELECT * FROM {TABLE_NAME} "
                f"WHERE seats >= %s "
                f"AND is_active = TRUE "
                f"ORDER BY seats;"
            )
            with driver._cursor() as cursor:
                cursor.execute(query, (min_seats,))
                return cursor.fetchall()

    # ----------------------------------------------------------- #
    # Обновление
    # ----------------------------------------------------------- #

    @staticmethod
    def update(
        driver: DatabaseDriver,
        table_id: int,
        table_number: Optional[str] = None,
        seats: Optional[int] = None,
        zone: Optional[str] = None,
    ) -> bool:
        """
        Обновляет данные стола.

        Возвращает:
            True при успешном обновлении, False — в случае ошибки.
        """
        if seats is not None and seats <= 0:
            raise ValueError("Количество мест должно быть больше нуля.")

        data = {"updated_at": datetime.now()}
        if table_number is not None:
            data["table_number"] = table_number
        if seats is not None:
            data["seats"] = seats
        if zone is not None:
            data["zone"] = zone

        updated = driver.update(TABLE_NAME, data, {"id": table_id})
        return updated > 0

    @staticmethod
    def deactivate(driver: DatabaseDriver, table_id: int) -> bool:
        """Деактивирует стол."""
        data = {"is_active": False, "updated_at": datetime.now()}
        updated = driver.update(TABLE_NAME, data, {"id": table_id})
        return updated > 0

    # ----------------------------------------------------------- #
    # Проверка существования
    # ----------------------------------------------------------- #

    @staticmethod
    def exists(
        driver: DatabaseDriver,
        table_number: Optional[str] = None,
        table_id: Optional[int] = None,
    ) -> bool:
        """
        Проверяет существование стола по номеру или ID.

        Возвращает:
            True, если стол найден.
        """
        if table_number:
            if driver.exists(TABLE_NAME, "table_number", table_number):
                return True
        if table_id:
            if driver.exists(TABLE_NAME, "id", table_id):
                return True
        return False
