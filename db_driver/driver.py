"""
Универсальный драйвер для работы с PostgreSQL.

Использует библиотеку psycopg (v3) и подключается через DSN-строку.
Предоставляет полный набор CRUD-методов для работы с таблицами.
"""

import os
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    import psycopg

import psycopg
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv(override=True)


class DatabaseDriver:
    """
    Универсальный драйвер для работы с базой данных PostgreSQL.

    Поддерживает полный набор CRUD-операций:
      - Create: create_table, insert, insert_many
      - Read:   select_all, select_by_id, select_by_field, exists, count
      - Update: update, update_field
      - Delete: delete, delete_all

    Параметры:
        db_name:   Имя базы данных.
        user:      Имя пользователя.
        password:  Пароль.
        host:      Адрес сервера (по умолчанию localhost).
        port:      Порт (по умолчанию 5432).
    """

    def __init__(
        self,
        db_name: str | None = None,
        user: str | None = None,
        password: str | None = None,
        host: str = "localhost",
        port: str = "5432",
    ):
        self.db_name = db_name or os.getenv("DB_NAME", "test")
        self.user = user or os.getenv("DB_USER", "testik")
        self.password = password or os.getenv("DB_PASSWORD", "")
        self.host = host or os.getenv("DB_HOST", "localhost")
        self.port = port or os.getenv("DB_PORT", "5432")

        self._connection = None

    # ------------------------------------------------------------------ #
    # Подключение / закрытие
    # ------------------------------------------------------------------ #

    def connect(self) -> "DatabaseDriver":
        """Устанавливает подключение к базе данных."""
        if self._connection and self._connection.closed == 0:
            return self  # Уже подключён

        dsn = (
            f"dbname={self.db_name} "
            f"user={self.user} "
            f"password={self.password} "
            f"host={self.host} "
            f"port={self.port}"
        )

        try:
            self._connection = psycopg.connect(dsn)
            print(f"✓ Подключено к базе данных: {self.db_name}")
        except psycopg.OperationalError as e:
            print(f"✗ Ошибка подключения: {e}")
            raise

        return self

    def close(self):
        """Закрывает подключение к базе данных."""
        if self._connection and self._connection.closed == 0:
            self._connection.close()
            print(f"✗ Подключение к базе данных {self.db_name} закрыто.")

    @property
    def is_connected(self) -> bool:
        """Возвращает True, если подключение активно."""
        return self._connection is not None and self._connection.closed == 0

    @contextmanager
    def _cursor(self, commit: bool = False):
        """
        Контекстный менеджер для работы с курсором.

        Параметры:
            commit:  Если True — автоматически делает commit после выполнения.
        """
        if not self.is_connected:
            raise RuntimeError(
                "Нет подключения к БД. Вызовите driver.connect() перед использованием."
            )

        with self._connection.cursor() as cursor:
            try:
                yield cursor
                if commit:
                    self._connection.commit()
            except Exception:
                self._connection.rollback()
                raise

    # ------------------------------------------------------------------ #
    # CREATE — Таблицы
    # ------------------------------------------------------------------ #

    def create_table(
        self,
        table_name: str,
        columns: dict[str, str],
        if_not_exists: bool = True,
    ) -> bool:
        """
        Создаёт таблицу с заданными колонками.

        Параметры:
            table_name:      Имя таблицы.
            columns:         Словарь {"имя_колонки": "тип_данных"}.
            if_not_exists:   Не делать ошибку, если таблица уже существует.

        Пример:
            driver.create_table("users", {
                "id": "SERIAL PRIMARY KEY",
                "name": "VARCHAR(100) NOT NULL",
                "email": "VARCHAR(255) UNIQUE",
            })
        """
        col_defs = ", ".join(f"{name} {definition}" for name, definition in columns.items())
        prefix = "IF NOT EXISTS " if if_not_exists else ""

        query = f"CREATE TABLE {prefix}{table_name} ({col_defs});"

        try:
            with self._cursor(commit=True) as cursor:
                cursor.execute(query)
            print(f"✓ Таблица '{table_name}' создана.")
            return True
        except psycopg.ProgrammingError as e:
            print(f"⚠ Ошибка при создании таблицы '{table_name}': {e}")
            return False

    # ------------------------------------------------------------------ #
    # CREATE — Записи
    # ------------------------------------------------------------------ #

    def insert(
        self,
        table_name: str,
        data: dict[str, Any],
        return_id: bool = False,
    ) -> Optional[int]:
        """
        Вставляет одну запись в таблицу.

        Параметры:
            table_name:  Имя таблицы.
            data:        Словарь {"колонка": значение}.
            return_id:   Если True — возвращает вставленный ID.

        Возвращает:
            ID вставленной записи (если return_id=True), иначе None.
        """
        if not data:
            return None

        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

        if return_id:
            query += " RETURNING id;"

        try:
            with self._cursor(commit=True) as cursor:
                cursor.execute(query, tuple(data.values()))
                if return_id:
                    row = cursor.fetchone()
                    inserted_id = row[0] if row else None
                    print(f"✓ Запись вставлена в '{table_name}', ID: {inserted_id}")
                    return inserted_id
                print(f"✓ Запись вставлена в '{table_name}'.")
                return None
        except psycopg.Error as e:
            print(f"✗ Ошибка вставки в '{table_name}': {e}")
            return None

    def insert_many(
        self,
        table_name: str,
        rows: list[dict[str, Any]],
    ) -> int:
        """
        Вставляет несколько записей за один запрос.

        Параметры:
            table_name:  Имя таблицы.
            rows:        Список словарей {"колонка": значение}.

        Возвращает:
            Количество вставленных записей.
        """
        if not rows:
            return 0

        columns = rows[0].keys()
        placeholders = ", ".join(["%s"] * len(columns))
        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders});"

        try:
            with self._cursor(commit=True) as cursor:
                cursor.executemany(query, [tuple(row.values()) for row in rows])
                count = cursor.rowcount
            print(f"✓ Вставлено {count} записей в '{table_name}'.")
            return count
        except psycopg.Error as e:
            print(f"✗ Ошибка пакетной вставки в '{table_name}': {e}")
            return 0

    # ------------------------------------------------------------------ #
    # READ — Записи
    # ------------------------------------------------------------------ #

    def select_all(
        self,
        table_name: str,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[tuple]:
        """
        Возвращает все записи из таблицы.

        Параметры:
            table_name:  Имя таблицы.
            order_by:    Опциональное условие ORDER BY (например, "id DESC").
            limit:       Опциональное ограничение количества записей.

        Возвращает:
            Список кортежей — все записи таблицы.
        """
        query = f"SELECT * FROM {table_name}"
        params: list = []

        if order_by:
            query += f" ORDER BY {order_by}"
        if limit:
            query += " LIMIT %s"
            params.append(limit)

        try:
            with self._cursor() as cursor:
                cursor.execute(query, params if params else None)
                rows = cursor.fetchall()
            print(f"✓ Получено {len(rows)} записей из '{table_name}'.")
            return rows
        except psycopg.Error as e:
            print(f"✗ Ошибка чтения из '{table_name}': {e}")
            return []

    def select_by_id(
        self,
        table_name: str,
        record_id: int,
    ) -> Optional[tuple]:
        """
        Возвращает одну запись по ID.

        Возвращает:
            Кортеж с записью или None, если не найдена.
        """
        query = f"SELECT * FROM {table_name} WHERE id = %s;"

        try:
            with self._cursor() as cursor:
                cursor.execute(query, (record_id,))
                row = cursor.fetchone()
            if row:
                print(f"✓ Запись найдена в '{table_name}', ID: {record_id}.")
            else:
                print(f"⚠ Запись с ID {record_id} не найдена в '{table_name}'.")
            return row
        except psycopg.Error as e:
            print(f"✗ Ошибка чтения из '{table_name}': {e}")
            return None

    def select_by_field(
        self,
        table_name: str,
        column: str,
        value: Any,
    ) -> list[tuple]:
        """
        Возвращает записи, где колонка совпадает со значением.

        Возвращает:
            Список кортежей с найденными записями.
        """
        query = f"SELECT * FROM {table_name} WHERE {column} = %s;"

        try:
            with self._cursor() as cursor:
                cursor.execute(query, (value,))
                rows = cursor.fetchall()
            print(f"✓ Найдено {len(rows)} записей в '{table_name}' по '{column}'.")
            return rows
        except psycopg.Error as e:
            print(f"✗ Ошибка чтения из '{table_name}': {e}")
            return []

    def exists(
        self,
        table_name: str,
        column: str,
        value: Any,
    ) -> bool:
        """
        Проверяет существование записи по колонке и значению.

        Возвращает:
            True, если запись найдена.
        """
        query = f"SELECT EXISTS(SELECT 1 FROM {table_name} WHERE {column} = %s);"

        try:
            with self._cursor() as cursor:
                cursor.execute(query, (value,))
                result = cursor.fetchone()
            return bool(result[0]) if result else False
        except psycopg.Error as e:
            print(f"✗ Ошибка проверки '{table_name}': {e}")
            return False

    def count(
        self,
        table_name: str,
        column: str | None = None,
        value: Any = None,
    ) -> int:
        """
        Возвращает количество записей в таблице.

        Можно указать условие для подсчёта по фильтру.
        """
        if column and value is not None:
            query = f"SELECT COUNT(*) FROM {table_name} WHERE {column} = %s;"
            params = (value,)
        else:
            query = f"SELECT COUNT(*) FROM {table_name};"
            params = None

        try:
            with self._cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.fetchone()
            return result[0] if result else 0
        except psycopg.Error as e:
            print(f"✗ Ошибка подсчёта '{table_name}': {e}")
            return 0

    # ------------------------------------------------------------------ #
    # UPDATE — Записи
    # ------------------------------------------------------------------ #

    def update(
        self,
        table_name: str,
        data: dict[str, Any],
        where: dict[str, Any],
    ) -> int:
        """
        Обновляет записи, удовлетворяющие условию.

        Параметры:
            table_name:  Имя таблицы.
            data:        Словарь {"колонка": новое_значение}.
            where:       Словарь {"колонка": значение_для_условия}.

        Возвращает:
            Количество обновлённых записей.
        """
        if not data or not where:
            return 0

        set_clause = ", ".join(f"{col} = %s" for col in data.keys())
        where_clause = " AND ".join(f"{col} = %s" for col in where.keys())
        query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause};"

        values = tuple(data.values()) + tuple(where.values())

        try:
            with self._cursor(commit=True) as cursor:
                cursor.execute(query, values)
                updated = cursor.rowcount
            print(f"✓ Обновлено {updated} записей в '{table_name}'.")
            return updated
        except psycopg.Error as e:
            print(f"✗ Ошибка обновления '{table_name}': {e}")
            return 0

    def update_field(
        self,
        table_name: str,
        column: str,
        new_value: Any,
        where_column: str,
        where_value: Any,
    ) -> int:
        """
        Обновляет одно поле в записи, удовлетворяющей условию.

        Возвращает:
            Количество обновлённых записей.
        """
        query = (
            f"UPDATE {table_name} SET {column} = %s "
            f"WHERE {where_column} = %s;"
        )

        try:
            with self._cursor(commit=True) as cursor:
                cursor.execute(query, (new_value, where_value))
                updated = cursor.rowcount
            print(f"✓ Обновлено {updated} записей в '{table_name}'.")
            return updated
        except psycopg.Error as e:
            print(f"✗ Ошибка обновления '{table_name}': {e}")
            return 0

    # ------------------------------------------------------------------ #
    # DELETE — Записи
    # ------------------------------------------------------------------ #

    def delete(
        self,
        table_name: str,
        where: dict[str, Any],
    ) -> int:
        """
        Удаляет записи, удовлетворяющие условию.

        Параметры:
            table_name:  Имя таблицы.
            where:       Словарь {"колонка": значение_для_условия}.

        Возвращает:
            Количество удалённых записей.
        """
        if not where:
            return 0

        where_clause = " AND ".join(f"{col} = %s" for col in where.keys())
        query = f"DELETE FROM {table_name} WHERE {where_clause};"

        try:
            with self._cursor(commit=True) as cursor:
                cursor.execute(query, tuple(where.values()))
                deleted = cursor.rowcount
            print(f"✓ Удалено {deleted} записей из '{table_name}'.")
            return deleted
        except psycopg.Error as e:
            print(f"✗ Ошибка удаления из '{table_name}': {e}")
            return 0

    def delete_all(self, table_name: str) -> int:
        """
        Удаляет все записи из таблицы.

        Возвращает:
            Количество удалённых записей.
        """
        query = f"DELETE FROM {table_name};"

        try:
            with self._cursor(commit=True) as cursor:
                cursor.execute(query)
                deleted = cursor.rowcount
            print(f"✓ Удалено {deleted} записей из '{table_name}'.")
            return deleted
        except psycopg.Error as e:
            print(f"✗ Ошибка удаления из '{table_name}': {e}")
            return 0

    def drop_table(self, table_name: str, if_exists: bool = True) -> bool:
        """
        Удаляет таблицу из базы данных.

        Параметры:
            table_name:  Имя таблицы.
            if_exists:   Не делать ошибку, если таблица не существует.
        """
        prefix = "IF EXISTS " if if_exists else ""
        query = f"DROP TABLE {prefix}{table_name};"

        try:
            with self._cursor(commit=True) as cursor:
                cursor.execute(query)
            print(f"✓ Таблица '{table_name}' удалена.")
            return True
        except psycopg.Error as e:
            print(f"✗ Ошибка удаления таблицы '{table_name}': {e}")
            return False

    # ------------------------------------------------------------------ #
    # Утилитарные методы
    # ------------------------------------------------------------------ #

    def execute_query(
        self,
        query: str,
        params: tuple | None = None,
        commit: bool = False,
    ) -> list[tuple] | None:
        """
        Выполняет произвольный SQL-запрос.

        Параметры:
            query:   SQL-запрос с плейсхолдерами %s.
            params:  Кортеж параметров.
            commit:  Если True — делает commit.

        Возвращает:
            Результат запроса (для SELECT) или None.
        """
        try:
            with self._cursor(commit=commit) as cursor:
                cursor.execute(query, params)

                # Для SELECT-запросов возвращаем результат
                if cursor.description:
                    rows = cursor.fetchall()
                    print(f"✓ Получено {len(rows)} строк.")
                    return rows
                return None
        except psycopg.Error as e:
            print(f"✗ Ошибка выполнения запроса: {e}")
            return None

    def table_exists(self, table_name: str) -> bool:
        """Проверяет, существует ли таблица в базе данных."""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            );
        """

        try:
            with self._cursor() as cursor:
                cursor.execute(query, (table_name,))
                result = cursor.fetchone()
            return bool(result[0]) if result else False
        except psycopg.Error as e:
            print(f"✗ Ошибка проверки таблицы '{table_name}': {e}")
            return False

    def get_columns(self, table_name: str) -> list[str]:
        """
        Возвращает список имён колонок таблицы.
        """
        query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
            ORDER BY ordinal_position;
        """

        try:
            with self._cursor() as cursor:
                cursor.execute(query, (table_name,))
                rows = cursor.fetchall()
            return [row[0] for row in rows]
        except psycopg.Error as e:
            print(f"✗ Ошибка получения колонок '{table_name}': {e}")
            return []

    def __enter__(self):
        """Поддержка контекстного менеджера."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие при выходе из контекста."""
        self.close()

    def __del__(self):
        """Деструктор — закрывает подключение при удалении объекта."""
        try:
            if self.is_connected:
                self.close()
        except AttributeError:
            pass  # Объект не полностью инициализирован
