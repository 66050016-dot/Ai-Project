import os
import sqlite3
from contextlib import contextmanager
from datetime import date

import pandas as pd

DB_PATH = os.getenv(
    "HEALTH_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "health.db"),
)


@contextmanager
def _conn():
    c = sqlite3.connect(DB_PATH)
    try:
        yield c
        c.commit()
    finally:
        c.close()


def _num(x):
    """แปลงเป็น float, ค่าว่าง/NaN ให้เป็น None (เก็บเป็น NULL)"""
    if x is None or pd.isna(x):
        return None
    return float(x)


def init_db():
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS profile (
                day TEXT PRIMARY KEY,
                gender TEXT, age INTEGER, weight REAL, height REAL,
                activity TEXT, goal TEXT, target_cal REAL
            );
            CREATE TABLE IF NOT EXISTS food_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day TEXT NOT NULL,
                meal TEXT, name TEXT, grams REAL,
                kcal REAL, protein REAL, carbs REAL, fat REAL
            );
            CREATE INDEX IF NOT EXISTS idx_food_day ON food_log(day);
            CREATE TABLE IF NOT EXISTS water_log (
                day TEXT PRIMARY KEY, liters REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS weight_log (
                day TEXT PRIMARY KEY, kg REAL NOT NULL
            );
            """
        )


# ---------- profile ----------
def save_profile(day: date, gender, age, weight, height, activity, goal, target_cal):
    """บันทึกข้อมูลผู้ใช้ของวันนั้น (เก็บแยกตามวัน เพื่อให้เป้าที่เปลี่ยนไม่ทำให้ประวัติเพี้ยน)"""
    with _conn() as c:
        c.execute(
            """INSERT INTO profile VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(day) DO UPDATE SET
                 gender=excluded.gender, age=excluded.age, weight=excluded.weight,
                 height=excluded.height, activity=excluded.activity,
                 goal=excluded.goal, target_cal=excluded.target_cal""",
            (day.isoformat(), gender, int(age), float(weight), float(height),
             activity, goal, float(target_cal)),
        )


def get_profiles(start: date, end: date) -> pd.DataFrame:
    with _conn() as c:
        return pd.read_sql_query(
            "SELECT * FROM profile WHERE day BETWEEN ? AND ? ORDER BY day",
            c, params=(start.isoformat(), end.isoformat()),
        )


# ---------- food ----------
def add_foods(rows: list[dict], day: date) -> int:
    """rows: dict ที่มีคีย์ อาหาร, กรัม, มื้อ, kcal, protein, carbs, fat"""
    data = []
    for r in rows:
        name = str(r.get("อาหาร") or "").strip()
        grams = _num(r.get("กรัม"))
        if not name or grams is None:
            continue
        data.append((
            day.isoformat(), r.get("มื้อ"), name, grams,
            _num(r.get("kcal")), _num(r.get("protein")),
            _num(r.get("carbs")), _num(r.get("fat")),
        ))
    with _conn() as c:
        c.executemany(
            "INSERT INTO food_log (day, meal, name, grams, kcal, protein, carbs, fat) "
            "VALUES (?,?,?,?,?,?,?,?)",
            data,
        )
    return len(data)


def get_foods(start: date, end: date) -> pd.DataFrame:
    with _conn() as c:
        return pd.read_sql_query(
            "SELECT * FROM food_log WHERE day BETWEEN ? AND ? ORDER BY day, id",
            c, params=(start.isoformat(), end.isoformat()),
        )


def delete_foods(ids: list[int]):
    if not ids:
        return
    with _conn() as c:
        c.executemany("DELETE FROM food_log WHERE id = ?", [(int(i),) for i in ids])


# ---------- water ----------
def add_water(day: date, liters: float):
    with _conn() as c:
        c.execute(
            """INSERT INTO water_log VALUES (?, ?)
               ON CONFLICT(day) DO UPDATE SET liters = liters + excluded.liters""",
            (day.isoformat(), float(liters)),
        )


def set_water(day: date, liters: float):
    with _conn() as c:
        c.execute(
            """INSERT INTO water_log VALUES (?, ?)
               ON CONFLICT(day) DO UPDATE SET liters = excluded.liters""",
            (day.isoformat(), max(float(liters), 0.0)),
        )


def get_water(start: date, end: date) -> pd.DataFrame:
    with _conn() as c:
        return pd.read_sql_query(
            "SELECT * FROM water_log WHERE day BETWEEN ? AND ? ORDER BY day",
            c, params=(start.isoformat(), end.isoformat()),
        )


# ---------- weight ----------
def set_weight(day: date, kg: float):
    with _conn() as c:
        c.execute(
            """INSERT INTO weight_log VALUES (?, ?)
               ON CONFLICT(day) DO UPDATE SET kg = excluded.kg""",
            (day.isoformat(), float(kg)),
        )


def get_weights(start: date, end: date) -> pd.DataFrame:
    with _conn() as c:
        return pd.read_sql_query(
            "SELECT * FROM weight_log WHERE day BETWEEN ? AND ? ORDER BY day",
            c, params=(start.isoformat(), end.isoformat()),
        )
