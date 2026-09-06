"""
DB Driver — универсальный модуль для работы с PostgreSQL.

Использование:
    from db_driver import DatabaseDriver

    db = DatabaseDriver(
        db_name="mydb",
        user="myuser",
        password="mypassword",
        host="localhost",
        port="5432"
    )
    db.connect()

    # CRUD-операции
    db.create_table("users", {
        "id": "SERIAL PRIMARY KEY",
        "name": "VARCHAR(100) NOT NULL",
        "email": "VARCHAR(255) UNIQUE",
        "age": "INTEGER",
    })

    db.insert("users", {"name": "Alice", "email": "alice@example.com", "age": 30})
    rows = db.select_all("users")
    user = db.select_by_id("users", 1)
    db.update("users", {"name": "Alice Updated"}, {"id": 1})
    db.delete("users", {"id": 1})

    db.close()
"""

from db_driver.driver import DatabaseDriver

__all__ = ["DatabaseDriver"]
__version__ = "1.0.0"
