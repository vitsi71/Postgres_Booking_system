"""
Модель пользователя для системы бронирования.

Класс User инкапсулирует:
  - SQL-схема таблицы users
  - Константы имён колонок
  - CRUD-операции через DatabaseDriver
"""

from datetime import datetime
from typing import Optional

from db_driver.driver import DatabaseDriver

# --------------------------------------------------------------- #
# Имена колонок и схема таблицы
# --------------------------------------------------------------- #

TABLE_NAME = "users"

SCHEMA: dict[str, str] = {
    "id": "SERIAL PRIMARY KEY",
    "username": "VARCHAR(100) UNIQUE NOT NULL",
    "email": "VARCHAR(255) UNIQUE NOT NULL",
    "full_name": "VARCHAR(255)",
    "phone": "VARCHAR(50)",
    "is_active": "BOOLEAN DEFAULT TRUE",
    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
}

# --------------------------------------------------------------- #
# Класс User
# --------------------------------------------------------------- #

class User:
    """Модель пользователя системы бронирования."""

    # ----------------------------------------------------------- #
    # Создание таблицы
    # ----------------------------------------------------------- #

    @staticmethod
    def create_table(driver: DatabaseDriver) -> bool:
        """Создаёт таблицу users в базе данных."""
        return driver.create_table(TABLE_NAME, SCHEMA)

    # ----------------------------------------------------------- #
    # Создание пользователя
    # ----------------------------------------------------------- #

    @staticmethod
    def insert(
        driver: DatabaseDriver,
        username: str,
        email: str,
        full_name: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Optional[int]:
        """
        Создаёт нового пользователя.

        Возвращает:
            ID созданной записи или None в случае ошибки.
        """
        now = datetime.now()
        data = {
            "username": username,
            "email": email,
            "full_name": full_name,
            "phone": phone,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        return driver.insert(TABLE_NAME, data, return_id=True)

    # ----------------------------------------------------------- #
    # Поиск пользователей
    # ----------------------------------------------------------- #

    @staticmethod
    def select_by_id(driver: DatabaseDriver, user_id: int) -> Optional[tuple]:
        """Возвращает запись пользователя по ID."""
        return driver.select_by_id(TABLE_NAME, user_id)

    @staticmethod
    def select_by_username(driver: DatabaseDriver, username: str) -> Optional[tuple]:
        """Возвращает запись пользователя по имени."""
        rows = driver.select_by_field(TABLE_NAME, "username", username)
        return rows[0] if rows else None

    @staticmethod
    def select_by_email(driver: DatabaseDriver, email: str) -> Optional[tuple]:
        """Возвращает запись пользователя по email."""
        rows = driver.select_by_field(TABLE_NAME, "email", email)
        return rows[0] if rows else None

    @staticmethod
    def select_all_active(driver: DatabaseDriver) -> list[tuple]:
        """Возвращает всех активных пользователей."""
        query = f"SELECT * FROM {TABLE_NAME} WHERE is_active = TRUE ORDER BY id;"
        with driver._cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    # ----------------------------------------------------------- #
    # Обновление
    # ----------------------------------------------------------- #

    @staticmethod
    def update(
        driver: DatabaseDriver,
        user_id: int,
        full_name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
    ) -> bool:
        """
        Обновляет данные пользователя.

        Возвращает:
            True при успешном обновлении, False — в случае ошибки.
        """
        data = {"updated_at": datetime.now()}
        if full_name is not None:
            data["full_name"] = full_name
        if phone is not None:
            data["phone"] = phone
        if email is not None:
            data["email"] = email

        updated = driver.update(TABLE_NAME, data, {"id": user_id})
        return updated > 0

    @staticmethod
    def deactivate(driver: DatabaseDriver, user_id: int) -> bool:
        """Деактивирует пользователя (soft delete)."""
        data = {"is_active": False, "updated_at": datetime.now()}
        updated = driver.update(TABLE_NAME, data, {"id": user_id})
        return updated > 0

    # ----------------------------------------------------------- #
    # Проверка существования
    # ----------------------------------------------------------- #

    @staticmethod
    def exists(
        driver: DatabaseDriver,
        username: Optional[str] = None,
        email: Optional[str] = None,
    ) -> bool:
        """
        Проверяет существование пользователя по username или email.

        Возвращает:
            True, если пользователь найден.
        """
        if username:
            if driver.exists(TABLE_NAME, "username", username):
                return True
        if email:
            if driver.exists(TABLE_NAME, "email", email):
                return True
        return False
