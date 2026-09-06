"""
Графический интерфейс для системы бронирования ресторана.
Tkinter с вкладками для управления пользователями, столами и бронированиями.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Optional

from db_driver.driver import DatabaseDriver
from backend import (
    # Инициализация
    init_db,
    # Users CRUD
    create_user, read_user, read_users_by_username,
    read_users_by_email, read_all_active_users,
    update_user, delete_user,
    # Tables CRUD
    create_table, read_table, read_table_by_number,
    read_all_active_tables, read_tables_by_seats,
    update_table, delete_table,
    # Bookings CRUD
    create_booking, read_booking, read_bookings_by_user,
    read_bookings_by_table, read_active_bookings,
    read_bookings_by_date, update_booking, delete_booking,
)


# =============================================================== #
# Глобальная сессия драйвера
# =============================================================== #

driver: Optional[DatabaseDriver] = None


def get_driver() -> DatabaseDriver:
    """Возвращает активный драйвер, создаёт новый при необходимости."""
    global driver
    if driver is None or not driver.is_connected:
        driver = DatabaseDriver()
        driver.connect()
    return driver


def close_driver():
    """Закрывает соединение с БД."""
    global driver
    if driver and driver.is_connected:
        driver.close()
        driver = None


# =============================================================== #
# Вспомогательные функции
# =============================================================== #

def clear_tree(tree: ttk.Treeview):
    """Очищает дерево."""
    for item in tree.get_children():
        tree.delete(item)


def show_message(title: str, message: str, level: str = "info"):
    """Показывает сообщение."""
    methods = {
        "info": messagebox.showinfo,
        "warning": messagebox.showwarning,
        "error": messagebox.showerror,
    }
    methods.get(level, messagebox.showinfo)(title, message)


def format_datetime(dt) -> str:
    """Форматирует datetime в строку."""
    if isinstance(dt, str):
        return dt
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M") if hasattr(dt, "strftime") else str(dt)


# =============================================================== #
# Кастомный календарь
# =============================================================== #

class CalendarPopup:
    """Простой календарь для выбора даты."""

    DAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    MONTHS_RU = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
    ]

    def __init__(self, parent, initial_date: datetime = None):
        self.result = None
        self.top = tk.Toplevel(parent)
        self.top.title("Выберите дату")
        self.top.resizable(False, False)
        self.top.transient(parent)
        self.top.grab_set()

        self.year = initial_date.year if initial_date else datetime.now().year
        self.month = initial_date.month if initial_date else datetime.now().month

        self._build_ui()

    def _build_ui(self):
        # --- Навигация ---
        nav = ttk.Frame(self.top)
        nav.pack(fill="x", padx=5, pady=5)

        ttk.Button(nav, text="◄", width=3, command=self._prev_month).pack(side="left", padx=5)
        self.lbl_month = ttk.Label(nav, text="", font=("Arial", 11, "bold"))
        self.lbl_month.pack(side="left", expand=True)
        ttk.Button(nav, text="►", width=3, command=self._next_month).pack(side="left", padx=5)

        # --- Сетка дней ---
        self.btn_days = []
        grid = ttk.Frame(self.top)
        grid.pack(padx=5, pady=5)

        for col, day_name in enumerate(self.DAYS_RU):
            ttk.Label(grid, text=day_name, font=("Arial", 9, "bold")).grid(row=0, column=col, padx=2, pady=2)

        for row in range(1, 8):
            for col in range(7):
                btn = ttk.Button(grid, text="", width=3, command=None)
                btn.grid(row=row, column=col, padx=1, pady=1)
                self.btn_days.append(btn)

        self._refresh_calendar()

    def _refresh_calendar(self):
        """Перерисовывает календарь."""
        self.lbl_month.config(text=f"{self.MONTHS_RU[self.month - 1]} {self.year}")

        # Первый день недели месяца (0=Пн ... 6=Вс)
        import calendar
        first_weekday = calendar.monthrange(self.year, self.month)[0]  # 0=Пн
        days_in_month = calendar.monthrange(self.year, self.month)[1]

        today = datetime.now().date()
        now_date = self.year, self.month, 1

        for i, btn in enumerate(self.btn_days):
            day_num = i - first_weekday + 1
            if 1 <= day_num <= days_in_month:
                btn.config(text=str(day_num), state="normal")
                d = datetime(self.year, self.month, day_num).date()
                if d == today:
                    btn.config(style="Today.TButton")
                else:
                    btn.config(style="")
                btn.config(command=lambda dn=day_num: self._select(dn))
            else:
                btn.config(text="", state="disabled")

    def _prev_month(self):
        self.month -= 1
        if self.month < 1:
            self.month = 12
            self.year -= 1
        self._refresh_calendar()

    def _next_month(self):
        self.month += 1
        if self.month > 12:
            self.month = 1
            self.year += 1
        self._refresh_calendar()

    def _select(self, day):
        self.result = datetime(self.year, self.month, day)
        self.top.destroy()

    def show(self):
        """Возвращает выбранную дату или None."""
        self.top.wait_window()
        return self.result


# =============================================================== #
# Вкладка: Инициализация БД
# =============================================================== #

class InitTab(ttk.Frame):
    """Вкладка инициализации базы данных."""

    def __init__(self, parent):
        super().__init__(parent)

        ttk.Label(self, text="Инициализация базы данных", font=("Arial", 14, "bold")).pack(pady=10)

        ttk.Label(self, text="Создаст все таблицы системы бронирования").pack(pady=5)

        btn = ttk.Button(self, text="Создать таблицы", command=self._create_tables)
        btn.pack(pady=10)

        self.log_text = tk.Text(self, height=8, width=60, state="disabled", font=("Courier", 9))
        self.log_text.pack(pady=10)

    def _log(self, msg: str):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _create_tables(self):
        try:
            self._log("Подключение к базе данных...")
            db = get_driver()
            self._log("✓ Подключено.")

            self._log("Создание таблиц...")
            init_db()
            self._log("✓ Все таблицы созданы успешно.")
            show_message("Готово", "Все таблицы созданы.")
        except Exception as e:
            self._log(f"✗ Ошибка: {e}")
            show_message("Ошибка", str(e), "error")


# =============================================================== #
# Вкладка: Пользователи
# =============================================================== #

class UsersTab(ttk.Frame):
    """Вкладка управления пользователями."""

    def __init__(self, parent):
        super().__init__(parent)

        # --- Верхняя часть: форма ---
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=5)

        ttk.Label(top, text="ID пользователя:").grid(row=0, column=0, padx=5, pady=2, sticky="e")
        self.var_user_id = ttk.Entry(top, width=6)
        self.var_user_id.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(top, text="Username:").grid(row=0, column=2, padx=5, pady=2, sticky="e")
        self.var_username = ttk.Entry(top, width=18)
        self.var_username.grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(top, text="Email:").grid(row=0, column=4, padx=5, pady=2, sticky="e")
        self.var_email = ttk.Entry(top, width=22)
        self.var_email.grid(row=0, column=5, padx=5, pady=2)

        ttk.Label(top, text="ФИО:").grid(row=0, column=6, padx=5, pady=2, sticky="e")
        self.var_full_name = ttk.Entry(top, width=18)
        self.var_full_name.grid(row=0, column=7, padx=5, pady=2)

        ttk.Label(top, text="Телефон:").grid(row=1, column=0, padx=5, pady=2, sticky="e")
        self.var_phone = ttk.Entry(top, width=18)
        self.var_phone.grid(row=1, column=1, padx=5, pady=2)

        # Кнопки действий
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(btn_frame, text="Создать", command=self._create).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="Обновить", command=self._update).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="Удалить", command=self._delete).pack(side="left", padx=3)

        # Поиск
        search_frame = ttk.Frame(btn_frame)
        search_frame.pack(side="left", padx=15)
        ttk.Label(search_frame, text="Поиск:").pack(side="left", padx=2)
        self.var_search = ttk.Entry(search_frame, width=20)
        self.var_search.pack(side="left", padx=2)
        ttk.Button(search_frame, text="По username", command=lambda: self._search("username")).pack(side="left", padx=2)
        ttk.Button(search_frame, text="По email", command=lambda: self._search("email")).pack(side="left", padx=2)

        ttk.Button(btn_frame, text="Все активные", command=self._load_all).pack(side="left", padx=3)

        # --- Таблица ---
        cols = ("id", "username", "email", "full_name", "phone", "is_active", "created_at", "updated_at")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)

        headings = {
            "id": "ID",
            "username": "Username",
            "email": "Email",
            "full_name": "ФИО",
            "phone": "Телефон",
            "is_active": "Активен",
            "created_at": "Создан",
            "updated_at": "Обновлён",
        }

        for col in cols:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=100, minwidth=60)

        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _get_driver(self):
        return get_driver()

    def _clear_fields(self):
        for var in [self.var_user_id, self.var_username, self.var_email,
                    self.var_full_name, self.var_phone]:
            var.delete(0, "end")

    def _row_to_fields(self, row):
        """Заполняет поля из строки таблицы."""
        self.var_user_id.delete(0, "end")
        self.var_user_id.insert(0, row[0])
        self.var_username.delete(0, "end")
        self.var_username.insert(0, row[1])
        self.var_email.delete(0, "end")
        self.var_email.insert(0, row[2])
        self.var_full_name.delete(0, "end")
        self.var_full_name.insert(0, row[3] or "")
        self.var_phone.delete(0, "end")
        self.var_phone.insert(0, row[4] or "")

    def _on_select(self, event):
        sel = self.tree.selection()
        if sel:
            item = self.tree.item(sel[0])
            self._row_to_fields(item["values"])

    def _load_row(self, row):
        """Добавляет одну строку в дерево."""
        created = format_datetime(row[6]) if len(row) > 6 else ""
        updated = format_datetime(row[7]) if len(row) > 7 else ""
        active = "Да" if row[5] else "Нет"
        self.tree.insert("", "end", values=(
            row[0], row[1], row[2],
            row[3] or "", row[4] or "", active, created, updated
        ))

    def _load_all(self):
        """Загружает всех активных пользователей."""
        try:
            rows = read_all_active_users(self._get_driver())
            clear_tree(self.tree)
            for row in rows:
                self._load_row(row)
        except Exception as e:
            show_message("Ошибка", str(e), "error")

    def _search(self, by: str):
        """Ищет пользователя."""
        value = self.var_search.get().strip()
        if not value:
            show_message("Внимание", "Введите значение для поиска.")
            return
        try:
            clear_tree(self.tree)
            if by == "username":
                row = read_users_by_username(self._get_driver(), value)
            else:
                row = read_users_by_email(self._get_driver(), value)
            if row:
                self._load_row(row)
            else:
                show_message("Не найдено", "Пользователь не найден.")
        except Exception as e:
            show_message("Ошибка", str(e), "error")

    def _create(self):
        """Создаёт пользователя."""
        username = self.var_username.get().strip()
        email = self.var_email.get().strip()
        if not username or not email:
            show_message("Внимание", "Заполните обязательные поля: username, email.")
            return
        try:
            user_id = create_user(
                self._get_driver(),
                username, email,
                self.var_full_name.get().strip() or None,
                self.var_phone.get().strip() or None,
            )
            if user_id:
                show_message("Готово", f"Пользователь создан. ID: {user_id}")
                self._clear_fields()
                self._load_all()
            else:
                show_message("Ошибка", "Не удалось создать пользователя.")
        except Exception as e:
            show_message("Ошибка", str(e), "error")

    def _update(self):
        """Обновляет пользователя."""
        user_id_str = self.var_user_id.get().strip()
        if not user_id_str:
            show_message("Внимание", "Введите ID пользователя.")
            return
        try:
            user_id = int(user_id_str)
            ok = update_user(
                self._get_driver(), user_id,
                self.var_full_name.get().strip() or None,
                self.var_phone.get().strip() or None,
                self.var_email.get().strip() or None,
            )
            if ok:
                show_message("Готово", "Пользователь обновлён.")
                self._load_all()
            else:
                show_message("Ошибка", "Не удалось обновить пользователя.")
        except ValueError:
            show_message("Ошибка", "ID должен быть числом.")
        except Exception as e:
            show_message("Ошибка", str(e), "error")

    def _delete(self):
        """Удаляет (деактивирует) пользователя."""
        user_id_str = self.var_user_id.get().strip()
        if not user_id_str:
            show_message("Внимание", "Введите ID пользователя.")
            return
        if not messagebox.askyesno("Подтверждение", "Деактивировать пользователя?"):
            return
        try:
            user_id = int(user_id_str)
            ok = delete_user(self._get_driver(), user_id)
            if ok:
                show_message("Готово", "Пользователь деактивирован.")
                self._clear_fields()
                self._load_all()
            else:
                show_message("Ошибка", "Не удалось деактивировать пользователя.")
        except ValueError:
            show_message("Ошибка", "ID должен быть числом.")
        except Exception as e:
            show_message("Ошибка", str(e), "error")


# =============================================================== #
# Вкладка: Столы
# =============================================================== #

class TablesTab(ttk.Frame):
    """Вкладка управления столами."""

    def __init__(self, parent):
        super().__init__(parent)

        # --- Форма ---
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=5)

        ttk.Label(top, text="ID стола:").grid(row=0, column=0, padx=5, pady=2, sticky="e")
        self.var_table_id = ttk.Entry(top, width=6)
        self.var_table_id.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(top, text="Номер:").grid(row=0, column=2, padx=5, pady=2, sticky="e")
        self.var_number = ttk.Entry(top, width=12)
        self.var_number.grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(top, text="Места:").grid(row=0, column=4, padx=5, pady=2, sticky="e")
        self.var_seats = ttk.Entry(top, width=6)
        self.var_seats.grid(row=0, column=5, padx=5, pady=2)

        ttk.Label(top, text="Зона:").grid(row=0, column=6, padx=5, pady=2, sticky="e")
        self.var_zone = ttk.Entry(top, width=18)
        self.var_zone.grid(row=0, column=7, padx=5, pady=2)

        # Кнопки
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(btn_frame, text="Создать", command=self._create).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="Обновить", command=self._update).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="Удалить", command=self._delete).pack(side="left", padx=3)

        search_frame = ttk.Frame(btn_frame)
        search_frame.pack(side="left", padx=15)
        ttk.Label(search_frame, text="Места от:").pack(side="left", padx=2)
        self.var_min_seats = ttk.Entry(search_frame, width=6)
        self.var_min_seats.pack(side="left", padx=2)
        ttk.Label(search_frame, text=" до:").pack(side="left", padx=2)
        self.var_max_seats = ttk.Entry(search_frame, width=6)
        self.var_max_seats.pack(side="left", padx=2)
        ttk.Button(search_frame, text="Найти", command=self._search_seats).pack(side="left", padx=2)

        ttk.Button(btn_frame, text="Все активные", command=self._load_all).pack(side="left", padx=3)

        # --- Таблица ---
        cols = ("id", "table_number", "seats", "zone", "is_active", "created_at", "updated_at")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)

        headings = {
            "id": "ID",
            "table_number": "Номер",
            "seats": "Места",
            "zone": "Зона",
            "is_active": "Активен",
            "created_at": "Создан",
            "updated_at": "Обновлён",
        }

        for col in cols:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=100, minwidth=60)

        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _get_driver(self):
        return get_driver()

    def _clear_fields(self):
        for var in [self.var_table_id, self.var_number, self.var_seats, self.var_zone]:
            var.delete(0, "end")

    def _on_select(self, event):
        sel = self.tree.selection()
        if sel:
            item = self.tree.item(sel[0])
            values = item["values"]
            self.var_table_id.delete(0, "end")
            self.var_table_id.insert(0, values[0])
            self.var_number.delete(0, "end")
            self.var_number.insert(0, values[1])
            self.var_seats.delete(0, "end")
            self.var_seats.insert(0, values[2])
            self.var_zone.delete(0, "end")
            self.var_zone.insert(0, values[3] or "")

    def _load_row(self, row):
        active = "Да" if row[4] else "Нет"
        created = format_datetime(row[5]) if len(row) > 5 else ""
        updated = format_datetime(row[6]) if len(row) > 6 else ""
        self.tree.insert("", "end", values=(
            row[0], row[1], row[2], row[3] or "", active, created, updated
        ))

    def _load_all(self):
        try:
            rows = read_all_active_tables(self._get_driver())
            clear_tree(self.tree)
            for row in rows:
                self._load_row(row)
        except Exception as e:
            show_message("Ошибка", str(e), "error")

    def _search_seats(self):
        min_s = self.var_min_seats.get().strip()
        max_s = self.var_max_seats.get().strip()
        if not min_s:
            show_message("Внимание", "Введите минимальное количество мест.")
            return
        try:
            clear_tree(self.tree)
            rows = read_tables_by_seats(
                self._get_driver(),
                int(min_s),
                int(max_s) if max_s else None,
            )
            for row in rows:
                self._load_row(row)
        except ValueError:
            show_message("Ошибка", "Введите корректные числа.")
        except Exception as e:
            show_message("Ошибка", str(e), "error")

    def _create(self):
        number = self.var_number.get().strip()
        seats_str = self.var_seats.get().strip()
        if not number or not seats_str:
            show_message("Внимание", "Заполните номер и количество мест.")
            return
        try:
            table_id = create_table(
                self._get_driver(),
                number, int(seats_str),
                self.var_zone.get().strip() or None,
            )
            if table_id:
                show_message("Готово", f"Стол создан. ID: {table_id}")
                self._clear_fields()
                self._load_all()
            else:
                show_message("Ошибка", "Не удалось создать стол.")
        except Exception as e:
            show_message("Ошибка", str(e), "error")

    def _update(self):
        table_id_str = self.var_table_id.get().strip()
        if not table_id_str:
            show_message("Внимание", "Введите ID стола.")
            return
        try:
            table_id = int(table_id_str)
            ok = update_table(
                self._get_driver(), table_id,
                self.var_number.get().strip() or None,
                int(self.var_seats.get().strip()) if self.var_seats.get().strip() else None,
                self.var_zone.get().strip() or None,
            )
            if ok:
                show_message("Готово", "Стол обновлён.")
                self._load_all()
            else:
                show_message("Ошибка", "Не удалось обновить стол.")
        except ValueError:
            show_message("Ошибка", "Проверьте корректность данных.")
        except Exception as e:
            show_message("Ошибка", str(e), "error")

    def _delete(self):
        table_id_str = self.var_table_id.get().strip()
        if not table_id_str:
            show_message("Внимание", "Введите ID стола.")
            return
        if not messagebox.askyesno("Подтверждение", "Деактивировать стол?"):
            return
        try:
            table_id = int(table_id_str)
            ok = delete_table(self._get_driver(), table_id)
            if ok:
                show_message("Готово", "Стол деактивирован.")
                self._clear_fields()
                self._load_all()
            else:
                show_message("Ошибка", "Не удалось деактивировать стол.")
        except ValueError:
            show_message("Ошибка", "ID должен быть числом.")
        except Exception as e:
            show_message("Ошибка", str(e), "error")


# =============================================================== #
# Вкладка: Бронирования
# =============================================================== #

class BookingsTab(ttk.Frame):
    """Вкладка управления бронированиями."""

    def __init__(self, parent):
        super().__init__(parent)

        # --- Форма: выбор пользователя и стола ---
        top1 = ttk.LabelFrame(self, text="Выбор заказчика и стола", padding=5)
        top1.pack(fill="x", padx=10, pady=5)

        ttk.Label(top1, text="Заказчик:").grid(row=0, column=0, padx=5, pady=2, sticky="e")
        self.combo_users = ttk.Combobox(top1, width=35, state="readonly")
        self.combo_users.grid(row=0, column=1, columnspan=2, padx=5, pady=2)
        self.combo_users.bind("<<ComboboxSelected>>", self._on_user_selected)
        ttk.Button(top1, text="Обновить", command=self._refresh_users).grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(top1, text="Стол:").grid(row=1, column=0, padx=5, pady=2, sticky="e")
        self.combo_tables = ttk.Combobox(top1, width=35, state="readonly")
        self.combo_tables.grid(row=1, column=1, columnspan=2, padx=5, pady=2)
        self.combo_tables.bind("<<ComboboxSelected>>", self._on_table_selected)
        ttk.Button(top1, text="Обновить", command=self._refresh_tables).grid(row=1, column=3, padx=5, pady=2)

        # --- Форма: дата и время ---
        top2 = ttk.LabelFrame(self, text="Дата и время", padding=5)
        top2.pack(fill="x", padx=10, pady=5)

        row = 0
        ttk.Label(top2, text="Дата:").grid(row=row, column=0, padx=5, pady=2, sticky="e")
        self.var_date = ttk.Entry(top2, width=14)
        self.var_date.grid(row=row, column=1, padx=5, pady=2)
        self.var_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        ttk.Button(top2, text="📅", width=2, command=self._open_calendar).grid(row=row, column=2, padx=2, pady=2)

        ttk.Label(top2, text="Начало:").grid(row=row, column=3, padx=5, pady=2, sticky="e")
        self.var_start_time = ttk.Entry(top2, width=8)
        self.var_start_time.grid(row=row, column=4, padx=5, pady=2)
        self.var_start_time.insert(0, "19:00")

        ttk.Label(top2, text="Конец:").grid(row=row, column=5, padx=5, pady=2, sticky="e")
        self.var_end_time = ttk.Entry(top2, width=8)
        self.var_end_time.grid(row=row, column=6, padx=5, pady=2)
        self.var_end_time.insert(0, "21:00")

        row = 1
        ttk.Label(top2, text="Гостей:").grid(row=row, column=0, padx=5, pady=2, sticky="e")
        self.var_guests = ttk.Entry(top2, width=8)
        self.var_guests.grid(row=row, column=1, padx=5, pady=2)
        self.var_guests.insert(0, "2")

        ttk.Label(top2, text="Заметки:").grid(row=row, column=2, padx=5, pady=2, sticky="e")
        self.var_notes = ttk.Entry(top2, width=22)
        self.var_notes.grid(row=row, column=3, columnspan=4, padx=5, pady=2)

        # --- Кнопки действий ---
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(btn_frame, text="✓ Проверить доступность", command=self._check_availability).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="Создать", command=self._create).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="Обновить", command=self._update).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="Удалить", command=self._delete).pack(side="left", padx=3)

        # --- Статус доступности ---
        self.availability_frame = ttk.LabelFrame(self, text="Статус доступности", padding=5)
        self.availability_frame.pack(fill="x", padx=10, pady=5)

        self.availability_label = ttk.Label(self.availability_frame, text="Нажмите 'Проверить доступность'", foreground="gray")
        self.availability_label.pack()

        self.conflicts_text = tk.Text(self.availability_frame, height=4, width=90, state="disabled", font=("Courier", 9))
        self.conflicts_text.pack(fill="x", pady=5)

        # --- Поиск ---
        search_frame = ttk.Frame(btn_frame)
        search_frame.pack(side="left", padx=20)

        ttk.Label(search_frame, text="Дата поиска:").pack(side="left", padx=2)
        self.var_search_date = ttk.Entry(search_frame, width=14)
        self.var_search_date.pack(side="left", padx=2)
        ttk.Button(search_frame, text="По дате", command=self._search_by_date).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Все активные", command=self._load_all).pack(side="left", padx=3)

        # --- Таблица бронирований ---
        cols = ("id", "table_info", "guests_count", "user_name", "start_time",
                "end_time", "status", "notes")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12)

        headings = {
            "id": "ID",
            "table_info": "Стол",
            "guests_count": "Гостей",
            "user_name": "Заказчик",
            "start_time": "Начало",
            "end_time": "Конец",
            "status": "Статус",
            "notes": "Заметки",
        }

        for col in cols:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=110, minwidth=80)

        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Загружаем данные при инициализации
        self._load_all()

    # --------------------------------------------------------------- #
    # Комбо-боксы
    # --------------------------------------------------------------- #

    def _get_driver(self):
        return get_driver()

    def _refresh_users(self):
        """Обновляет список пользователей."""
        try:
            rows = read_all_active_users(self._get_driver())
            items = []
            for row in rows:
                user_id = row[0]
                full_name = row[3] or ""
                username = row[1]
                display = f"{user_id}: {full_name or username}"
                items.append(display)
            self.combo_users["values"] = items
            if items:
                self.combo_users.current(0)
        except Exception as e:
            show_message("Ошибка", str(e), "error")

    def _refresh_tables(self):
        """Обновляет список столов."""
        try:
            rows = read_all_active_tables(self._get_driver())
            items = []
            for row in rows:
                table_id = row[0]
                number = row[1]
                zone = row[3] or ""
                seats = row[2]
                display = f"{table_id}: {number} ({seats} мест, {zone})"
                items.append(display)
            self.combo_tables["values"] = items
            if items:
                self.combo_tables.current(0)
        except Exception as e:
            show_message("Ошибка", str(e), "error")

    def _on_user_selected(self, event):
        """При выборе пользователя сохраняем ID."""
        selected = self.combo_users.get()
        if selected:
            parts = selected.split(":", 1)
            try:
                self.var_user_id = int(parts[0].strip())
            except ValueError:
                self.var_user_id = None
        else:
            self.var_user_id = None

    def _on_table_selected(self, event):
        """При выборе стола сохраняем ID."""
        selected = self.combo_tables.get()
        if selected:
            parts = selected.split(":", 1)
            try:
                self.var_table_id = int(parts[0].strip())
            except ValueError:
                self.var_table_id = None
        else:
            self.var_table_id = None

    # --------------------------------------------------------------- #
    # Календарь
    # --------------------------------------------------------------- #

    def _open_calendar(self):
        """Открывает календарь для выбора даты."""
        try:
            initial = datetime.strptime(self.var_date.get(), "%Y-%m-%d")
        except ValueError:
            initial = None
        popup = CalendarPopup(self, initial)
        result = popup.show()
        if result:
            self.var_date.delete(0, "end")
            self.var_date.insert(0, result.strftime("%Y-%m-%d"))

    # --------------------------------------------------------------- #
    # Очистка формы
    # --------------------------------------------------------------- #

    def _clear_form(self):
        """Очищает поля формы."""
        self.var_guests.delete(0, "end")
        self.var_guests.insert(0, "2")
        self.var_notes.delete(0, "end")
        self.var_start_time.delete(0, "end")
        self.var_start_time.insert(0, "19:00")
        self.var_end_time.delete(0, "end")
        self.var_end_time.insert(0, "21:00")
        self.availability_label.config(text="Нажмите 'Проверить доступность'", foreground="gray")
        self.conflicts_text.config(state="normal")
        self.conflicts_text.delete("1.0", "end")
        self.conflicts_text.config(state="disabled")

    # --------------------------------------------------------------- #
    # Загрузка данных в таблицу
    # --------------------------------------------------------------- #

    def _on_select(self, event):
        """При выборе строки заполняет форму."""
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        values = item["values"]
        self.var_booking_id = values[0]

        table_info_displayed = values[1]
        user_name_displayed = values[3]

        # Ищем пользователя в комбо
        try:
            rows = read_all_active_users(self._get_driver())
            for row in rows:
                name = row[3] or row[1]
                if name == user_name_displayed:
                    idx = [r[0] for r in rows].index(row[0])
                    self.combo_users.current(idx)
                    break
        except Exception:
            pass

        # Ищем стол в комбо
        try:
            rows = read_all_active_tables(self._get_driver())
            for row in rows:
                table_label = f"{row[1]} ({row[2]} мест, {row[3] or '—'})"
                if table_label == table_info_displayed:
                    idx = [r[0] for r in rows].index(row[0])
                    self.combo_tables.current(idx)
                    break
        except Exception:
            pass

        # Время
        start_str = str(values[4]) if len(values) > 4 else ""
        if start_str:
            try:
                dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
                self.var_date.delete(0, "end")
                self.var_date.insert(0, dt.strftime("%Y-%m-%d"))
                self.var_start_time.delete(0, "end")
                self.var_start_time.insert(0, dt.strftime("%H:%M"))
            except ValueError:
                pass

        end_str = str(values[5]) if len(values) > 5 else ""
        if end_str:
            try:
                dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
                self.var_end_time.delete(0, "end")
                self.var_end_time.insert(0, dt.strftime("%H:%M"))
            except ValueError:
                pass

        self.var_guests.delete(0, "end")
        self.var_guests.insert(0, str(values[2]) if len(values) > 2 and values[2] else "2")
        self.var_notes.delete(0, "end")
        self.var_notes.insert(0, values[7] or "")

    def _load_all(self):
        """Загружает все активные бронирования."""
        try:
            rows = read_active_bookings(self._get_driver())
            clear_tree(self.tree)
            for row in rows:
                self._enrich_booking_row(row)
        except Exception as e:
            show_message("Ошибка", str(e), "error")

    def _enrich_booking_row(self, row):
        """
        Обогащает строку бронирования: добавляет имя пользователя и информацию о столе.
        
        row из БД: (id, user_id, table_id, start_time, end_time,
                    guests_count, status, notes, created_at, updated_at)
        """
        user_id = row[1]
        table_id = row[2]

        # Получаем ФИО пользователя
        user_full_name = ""
        try:
            user = read_user(self._get_driver(), user_id)
            if user:
                # (id, username, email, full_name, phone, is_active, created_at, updated_at)
                user_full_name = user[3] or user[1]
        except Exception:
            pass

        # Получаем информацию о столе
        table_label = ""
        try:
            table = read_table(self._get_driver(), table_id)
            if table:
                # (id, table_number, seats, zone, is_active, created_at, updated_at)
                table_label = f"{table[1]} ({table[2]} мест, {table[3] or '—'})"
        except Exception:
            pass

        # Форматируем время
        start = format_datetime(row[3]) if len(row) > 3 else ""
        end = format_datetime(row[4]) if len(row) > 4 else ""
        guests = row[5] if len(row) > 5 else ""
        status = row[6] if len(row) > 6 else ""
        notes = row[7] if len(row) > 7 else ""

        self.tree.insert("", "end", values=(
            row[0],       # id
            table_label,  # table_info
            guests,       # guests_count
            user_full_name,  # user_name
            start,        # start_time
            end,          # end_time
            status,       # status
            notes,        # notes
        ))

    # --------------------------------------------------------------- #
    # Проверка доступности
    # --------------------------------------------------------------- #

    def _get_table_seats(self, table_id):
        """Возвращает количество мест стола."""
        try:
            table = read_table(self._get_driver(), table_id)
            if table:
                return table[2]
        except Exception:
            pass
        return 0

    def _check_availability(self):
        """Проверяет доступность стола и вместимость."""
        table_id = getattr(self, "var_table_id", None)
        user_id = getattr(self, "var_user_id", None)
        date_str = self.var_date.get().strip()
        start_str = self.var_start_time.get().strip()
        end_str = self.var_end_time.get().strip()
        guests_str = self.var_guests.get().strip()

        if not user_id:
            show_message("Внимание", "Выберите заказчика.")
            return
        if not table_id:
            show_message("Внимание", "Выберите стол.")
            return
        if not date_str or not start_str or not end_str:
            show_message("Внимание", "Заполните дату и время.")
            return
        if not guests_str:
            show_message("Внимание", "Укажите количество гостей.")
            return

        try:
            guests = int(guests_str)
            date = datetime.strptime(date_str, "%Y-%m-%d")
            start = datetime.combine(date, datetime.strptime(start_str, "%H:%M").time())
            end = datetime.combine(date, datetime.strptime(end_str, "%H:%M").time())
        except ValueError:
            show_message("Ошибка", "Неверный формат даты или времени.")
            return

        # Проверяем вместимость стола
        seats = self._get_table_seats(table_id)
        warnings = []
        if guests > seats:
            warnings.append(f"⚠ Гости ({guests}) > мест в столе ({seats})")

        # Проверяем время
        from backend import check_table_availability
        is_available, conflicts = check_table_availability(
            self._get_driver(), table_id, start, end
        )

        self.conflicts_text.config(state="normal")
        self.conflicts_text.delete("1.0", "end")

        all_warnings = warnings.copy()

        if not is_available:
            all_warnings.append("✗ Стол занят в это время")
            for conflict in conflicts:
                c_id = conflict[0]
                c_start = format_datetime(conflict[3])
                c_end = format_datetime(conflict[4])
                c_guests = conflict[5]
                c_notes = conflict[7] or ""
                self.conflicts_text.insert("end",
                    f"  Конфликт ID:{c_id} | {c_start}-{c_end} | {c_guests} гостей | {c_notes}\n"
                )

        self.conflicts_text.config(state="disabled")

        if all_warnings:
            self.availability_label.config(
                text="✗ ЕСТЬ ПРОБЛЕМЫ — " + "; ".join(all_warnings),
                foreground="red",
            )
        else:
            self.availability_label.config(
                text="✓ СТОЛ СВОБОДЕН — можно создавать",
                foreground="green",
            )

    # --------------------------------------------------------------- #
    # Создание бронирования
    # --------------------------------------------------------------- #

    def _create(self):
        """Создаёт бронирование с проверкой доступности."""
        table_id = getattr(self, "var_table_id", None)
        user_id = getattr(self, "var_user_id", None)
        date_str = self.var_date.get().strip()
        start_str = self.var_start_time.get().strip()
        end_str = self.var_end_time.get().strip()
        guests_str = self.var_guests.get().strip()

        if not user_id:
            show_message("Внимание", "Выберите заказчика.")
            return
        if not table_id:
            show_message("Внимание", "Выберите стол.")
            return
        if not date_str or not start_str or not end_str or not guests_str:
            show_message("Внимание", "Заполните дату, время и гостей.")
            return

        try:
            guests = int(guests_str)
            date = datetime.strptime(date_str, "%Y-%m-%d")
            start = datetime.combine(date, datetime.strptime(start_str, "%H:%M").time())
            end = datetime.combine(date, datetime.strptime(end_str, "%H:%M").time())
        except ValueError:
            show_message("Ошибка", "Неверный формат данных.")
            return

        # === ПРОВЕРКА ДОСТУПНОСТИ ПЕРЕД СОЗДАНИЕМ ===
        seats = self._get_table_seats(table_id)
        warnings = []

        if guests > seats:
            warnings.append(f"Гостей ({guests}) больше мест в столе ({seats})")

        from backend import check_table_availability
        is_available, conflicts = check_table_availability(
            self._get_driver(), table_id, start, end
        )

        if not is_available:
            warnings.append("Стол занят в это время")
            for c in conflicts:
                c_start = format_datetime(c[3])
                c_end = format_datetime(c[4])
                warnings.append(f"Конфликт: {c_start}-{c_end}")

        if warnings:
            warning_text = "\n".join(warnings)
            result = messagebox.askyesnocancel(
                "⚠ Предупреждения",
                f"Есть проблемы:\n\n{warning_text}\n\n"
                "Хотите создать бронирование?\n"
                "(Да — создать, Нет — отменить, Отмена — закрыть)",
            )
            if result is None:  # Отмена
                return
            if result is False:  # Нет
                return

        # === СОЗДАНИЕ ===
        notes = self.var_notes.get().strip() or ""
        if warnings:
            if notes:
                notes += " | "
            notes += "ВНИМАНИЕ: " + "; ".join(warnings)

        try:
            booking_id = create_booking(
                self._get_driver(),
                user_id, table_id, start, end, guests, notes=notes,
            )
            if booking_id:
                show_message("Готово", f"Бронирование создано. ID: {booking_id}")
                self._clear_form()
                self._load_all()
            else:
                show_message("Ошибка", "Не удалось создать бронирование.")
        except ValueError as e:
            show_message("Ошибка", str(e))
        except Exception as e:
            show_message("Ошибка", str(e), "error")

    # --------------------------------------------------------------- #
    # Обновление / Удаление
    # --------------------------------------------------------------- #

    def _update(self):
        booking_id = getattr(self, "var_booking_id", None)
        if not booking_id:
            show_message("Внимание", "Выберите бронирование для обновления.")
            return

        date_str = self.var_date.get().strip()
        start_str = self.var_start_time.get().strip()
        end_str = self.var_end_time.get().strip()
        notes = self.var_notes.get().strip() or None

        start = datetime.strptime(f"{date_str} {start_str}", "%Y-%m-%d %H:%M") if date_str and start_str else None
        end = datetime.strptime(f"{date_str} {end_str}", "%Y-%m-%d %H:%M") if date_str and end_str else None

        try:
            ok = update_booking(self._get_driver(), booking_id, start, end, notes=notes)
            if ok:
                show_message("Готово", "Бронирование обновлено.")
                self._load_all()
            else:
                show_message("Ошибка", "Не удалось обновить.")
        except Exception as e:
            show_message("Ошибка", str(e), "error")

    def _delete(self):
        booking_id = getattr(self, "var_booking_id", None)
        if not booking_id:
            show_message("Внимание", "Выберите бронирование для удаления.")
            return
        if not messagebox.askyesno("Подтверждение", "Отменить бронирование?"):
            return
        try:
            ok = delete_booking(self._get_driver(), booking_id)
            if ok:
                show_message("Готово", "Бронирование отменено.")
                self._clear_form()
                self._load_all()
            else:
                show_message("Ошибка", "Не удалось отменить.")
        except Exception as e:
            show_message("Ошибка", str(e), "error")

    # --------------------------------------------------------------- #
    # Поиск
    # --------------------------------------------------------------- #

    def _search_by_date(self):
        date_str = self.var_search_date.get().strip()
        if not date_str:
            show_message("Внимание", "Введите дату (YYYY-MM-DD).")
            return
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            rows = read_bookings_by_date(self._get_driver(), date)
            clear_tree(self.tree)
            for row in rows:
                self._enrich_booking_row(row)
        except ValueError:
            show_message("Ошибка", "Неверный формат даты.")
        except Exception as e:
            show_message("Ошибка", str(e), "error")


# =============================================================== #
# Главное окно
# =============================================================== #

def create_gui():
    """Создаёт и запускает главное окно приложения."""
    root = tk.Tk()
    root.title("Ресторан — Система бронирования")
    root.geometry("1200x700")

    # --- TabControl ---
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    # Вкладки
    users_frame = UsersTab(notebook)
    tables_frame = TablesTab(notebook)
    bookings_frame = BookingsTab(notebook)

    notebook.add(InitTab(notebook), text="⚙ Инициализация")
    notebook.add(users_frame, text="👤 Пользователи")
    notebook.add(tables_frame, text="🪑 Столы")
    notebook.add(bookings_frame, text="📋 Бронирования")

    # Закрытие при выходе
    root.protocol("WM_DELETE_WINDOW", lambda: (close_driver(), root.destroy()))

    root.mainloop()


if __name__ == "__main__":
    create_gui()
