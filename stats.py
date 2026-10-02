from datetime import date, timedelta

import numpy as np
import pandas as pd

import database as db

MACRO_COLS = ["kcal", "protein", "carbs", "fat"]


def protein_guideline(weight_kg: float, goal: str) -> float:
    """ค่าโปรตีนโดยประมาณ (กรัม/วัน) แบบแนวทางทั่วไป ไม่ใช่คำแนะนำทางการแพทย์"""
    per_kg = {"เพิ่มกล้ามเนื้อ": 1.6, "ลดน้ำหนัก": 1.4}.get(goal, 1.2)
    return round(weight_kg * per_kg)


def daily_table(start: date, end: date) -> pd.DataFrame:
    """ตารางรายวันครบทุกวันในช่วง (วันที่ไม่ได้บันทึกจะเป็น logged=False)"""
    idx = pd.date_range(start, end, freq="D")
    df = pd.DataFrame({"day": idx})

    foods = db.get_foods(start, end)
    if not foods.empty:
        foods["day"] = pd.to_datetime(foods["day"])
        g = foods.groupby("day")[MACRO_COLS].sum(min_count=1).reset_index()
        df = df.merge(g, on="day", how="left")
        df["logged"] = df["day"].isin(foods["day"].unique())
    else:
        for c in MACRO_COLS:
            df[c] = np.nan
        df["logged"] = False

    water = db.get_water(start, end)
    water["day"] = pd.to_datetime(water["day"])
    df = df.merge(water.rename(columns={"liters": "water"}), on="day", how="left")

    wt = db.get_weights(start, end)
    wt["day"] = pd.to_datetime(wt["day"])
    df = df.merge(wt.rename(columns={"kg": "weight"}), on="day", how="left")
    return df


def current_streak(today: date | None = None) -> int:
    """จำนวนวันติดต่อกันที่บันทึกอาหาร (ถ้าวันนี้ยังไม่บันทึก นับต่อจากเมื่อวาน)"""
    today = today or date.today()
    foods = db.get_foods(today - timedelta(days=365), today)
    if foods.empty:
        return 0
    days = set(pd.to_datetime(foods["day"]).dt.date)
    d = today if today in days else today - timedelta(days=1)
    n = 0
    while d in days:
        n += 1
        d -= timedelta(days=1)
    return n


def _r(x, nd=0):
    return None if x is None or pd.isna(x) else round(float(x), nd)


def build_summary(days: int, target_cal: float, protein_target: float, goal: str,
                  today: date | None = None) -> dict:
    """สรุปตัวเลขที่ 'คำนวณด้วยโค้ด' แล้ว เพื่อส่งให้ AI ตีความ (ไม่ส่งข้อมูลดิบ/ข้อมูลระบุตัวตน)"""
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    df = daily_table(start, today)
    logged = df[df["logged"]]
    n = len(logged)

    summary = {
        "goal": goal,
        "period_days": days,
        "days_logged": n,
        "target_kcal": _r(target_cal),
        "protein_target_g": _r(protein_target),
        "streak_days": current_streak(today),
    }

    if n:
        summary.update({
            "avg_kcal": _r(logged["kcal"].mean()),
            "avg_protein_g": _r(logged["protein"].mean()),
            "avg_carbs_g": _r(logged["carbs"].mean()),
            "avg_fat_g": _r(logged["fat"].mean()),
            "days_over_target_10pct": int((logged["kcal"] > target_cal * 1.1).sum()),
            "days_under_target_10pct": int((logged["kcal"] < target_cal * 0.9).sum()),
            "days_protein_below_target": int((logged["protein"] < protein_target * 0.9).sum()),
        })
        avg_kcal = logged["kcal"].mean()
        if avg_kcal and avg_kcal > 0:
            summary["macro_share_pct"] = {
                "protein": _r(logged["protein"].mean() * 4 / avg_kcal * 100),
                "carbs": _r(logged["carbs"].mean() * 4 / avg_kcal * 100),
                "fat": _r(logged["fat"].mean() * 9 / avg_kcal * 100),
            }

    water = df["water"].dropna()
    if len(water):
        summary["avg_water_l"] = _r(water.mean(), 2)
        summary["days_water_logged"] = int(len(water))

    # แนวโน้มน้ำหนักใช้ช่วง 30 วันเสมอ เพราะน้ำหนักเปลี่ยนช้า
    w30 = db.get_weights(today - timedelta(days=29), today)
    if len(w30) >= 2:
        x = pd.to_datetime(w30["day"]).map(pd.Timestamp.toordinal).to_numpy(dtype=float)
        y = w30["kg"].to_numpy(dtype=float)
        slope_per_day = np.polyfit(x, y, 1)[0] if x.max() > x.min() else 0.0
        summary["weight_first_kg"] = _r(y[0], 1)
        summary["weight_last_kg"] = _r(y[-1], 1)
        summary["weight_trend_kg_per_week"] = _r(slope_per_day * 7, 2)
        summary["weight_points"] = int(len(w30))

    return summary
