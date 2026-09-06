# DB Driver — Документация

Универсальный модуль-драйвер для работы с PostgreSQL. Построен на основе библиотеки `psycopg` (v3) и использует DSN-строку для подключения.

## 📦 Установка

### Требования

- Python 3.10+
- PostgreSQL
- Зависимости:

```bash
pip install psycopg python-dotenv
```

### Подключение к вашему проекту

Модуль находится в папке `db_driver/`. Для использования скопируйте эту папку в ваш проект или добавьте как подмодуль.

## 🚀 Быстрый старт

### 1. Настройка подключения

Параметры подключения можно задать тремя способами:

#### Способ A: Передача в конструктор

```python
from db_driver import DatabaseDriver

db = DatabaseDriver(
    db_name="my_database",
    user="my_user",
    password="my_password",
    host="localhost",
    port="5432"
)
db.connect()
```

#### Способ B: Через файл `.env`

Создайте файл `.env` в корне проекта:

```env
DB_NAME=my_database
DB_USER=my_user
DB_PASSWORD=my_password
DB_HOST=localhost
DB_PORT=5432
```

Затем подключите без параметров:

```python
from db_driver import DatabaseDriver

db = DatabaseDriver()
db.connect()
```

#### Способ C: Контекстный менеджер (рекомендуется)

```python
from db_driver import DatabaseDriver

with DatabaseDriver(db_name="mydb", user="user", password="pass") as db:
    # База подключена
    db.create_table("users", {"id": "SERIAL PRIMARY KEY", "name": "VARCHAR(100)"})
    db.insert("users", {"name": "Alice"})
# База автоматически закрывается
```

## 📖 CRUD-операции

### CREATE — Создание таблиц

```python
# Создание таблицы с колонками
db.create_table("users", {
    "id": "SERIAL PRIMARY KEY",
    "name": "VARCHAR(100) NOT NULL",
    "email": "VARCHAR(255) UNIQUE",
    "age": "INTEGER",
    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
})
```

### CREATE — Вставка записей

```python
# Одна запись
db.insert("users", {"name": "Иван", "email": "ivan@mail.ru", "age": 30})

# С возвратом ID
user_id = db.insert("users", {"name": "Мария", "email": "maria@mail.ru"}, return_id=True)
print(f"Создан пользователь с ID: {user_id}")

# Пакетная вставка
db.insert_many("users", [
    {"name": "Алексей", "email": "alex@mail.ru", "age": 25},
    {"name": "Елена", "email": "elena@mail.ru", "age": 28},
    {"name": "Дмитрий", "email": "dmitry@mail.ru", "age": 35},
])
```

### READ — Чтение данных

```python
# Все записи
users = db.select_all("users")
for user in users:
    print(user)

# С сортировкой и лимитом
young_users = db.select_all("users", order_by="age ASC", limit=10)

# По ID
user = db.select_by_id("users", 1)

# По произвольному полю
users_by_email = db.select_by_field("users", "email", "ivan@mail.ru")

# Проверка существования
exists = db.exists("users", "email", "ivan@mail.ru")
print(f"Пользователь существует: {exists}")

# Подсчёт записей
total = db.count("users")
active = db.count("users", "age", 30)
```

### UPDATE — Обновление

```python
# Обновление нескольких полей
db.update("users", {"name": "ИванUpdated", "age": 31}, {"id": 1})

# Обновление одного поля
db.update_field("users", "age", 99, "email", "maria@mail.ru")
```

### DELETE — Удаление

```python
# Удаление по условию
deleted = db.delete("users", {"id": 1})
print(f"Удалено записей: {deleted}")

# Очистка таблицы
db.delete_all("users")

# Удаление таблицы
db.drop_table("users")
```

## 🛠 Утилитарные методы

### Проверка существования таблицы

```python
if db.table_exists("users"):
    print("Таблица существует")
```

### Получение колонок таблицы

```python
columns = db.get_columns("users")
print(columns)  # ['id', 'name', 'email', 'age', 'created_at']
```

### Произвольный SQL-запрос

```python
# SELECT
result = db.execute_query("SELECT * FROM users WHERE age > %s;", (25,))

# Произвольный запрос с commit
db.execute_query("DELETE FROM users WHERE age < 18;", commit=True)
```

### Проверка статуса подключения

```python
if db.is_connected:
    print("Подключено к базе данных")
```

## 📋 Полный пример

```python
from db_driver import DatabaseDriver

# Подключение
db = DatabaseDriver(
    db_name="mydb",
    user="myuser",
    password="mypassword"
)
db.connect()

# Создание таблицы
db.create_table("products", {
    "id": "SERIAL PRIMARY KEY",
    "name": "VARCHAR(200) NOT NULL",
    "price": "DECIMAL(10, 2)",
    "quantity": "INTEGER DEFAULT 0"
})

# Вставка
db.insert("products", {"name": "Ноутбук", "price": 50000, "quantity": 10})
db.insert_many("products", [
    {"name": "Мышь", "price": 1500, "quantity": 50},
    {"name": "Клавиатура", "price": 3000, "quantity": 30}
])

# Чтение
all_products = db.select_all("products")
expensive = db.select_by_field("products", "price", 50000)

# Обновление
db.update("products", {"quantity": 9}, {"name": "Ноутбук"})

# Удаление
db.delete("products", {"name": "Мышь"})

# Закрытие
db.close()
```

## 🔒 Безопасность

- Все параметры передаются через плейсхолдеры `%s` — защита от SQL-инъекций.
- Пароли храните в файле `.env`, не_hardкордите их в коде.
- Добавляйте `.env` в `.gitignore`.

## 🐛 Обработка ошибок

Драйвер автоматически выводит ошибки в консоль. Для обработки исключений используйте `try/except`:

```python
from db_driver import DatabaseDriver
import psycopg

try:
    db = DatabaseDriver(db_name="nonexistent", user="user", password="pass")
    db.connect()
except psycopg.OperationalError as e:
    print(f"Не удалось подключиться: {e}")
```

## 📝 Лицензия

Модуль распространяется как часть проекта. Используйте свободно в своих проектах.
