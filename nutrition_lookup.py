import os

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

USDA_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
THAI_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thai_foods.csv")

# รหัสสารอาหารของ USDA FoodData Central (ต่อ 100 กรัม)
NUTRIENT_IDS = {
    1008: "kcal",     # Energy
    1003: "protein",  # Protein
    1005: "carbs",    # Carbohydrate
    1004: "fat",      # Total fat
}


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def lookup_per_100g(name_en: str) -> dict | None:
    """ค้นหาโภชนาการต่อ 100 กรัมจาก USDA ถ้าไม่เจอคืน None (ไม่เดาตัวเลข)"""
    key = os.getenv("USDA_API_KEY", "DEMO_KEY")
    try:
        r = requests.get(
            USDA_URL,
            params={
                "api_key": key,
                "query": name_en,
                "pageSize": 1,
                "dataType": "Foundation,SR Legacy",
            },
            timeout=10,
        )
        r.raise_for_status()
        foods = r.json().get("foods", [])
        if not foods:
            return None

        result = {"kcal": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
        for n in foods[0].get("foodNutrients", []):
            label = NUTRIENT_IDS.get(n.get("nutrientId"))
            if label:
                result[label] = float(n.get("value", 0))
        if result["kcal"] <= 0:
            return None
        result["matched_name"] = foods[0].get("description", name_en)
        return result
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def _load_thai_table(mtime: float) -> dict:
    """อ่าน thai_foods.csv (mtime ใช้เป็น key เพื่อให้แคชรีเฟรชเมื่อแก้ไฟล์)"""
    if not os.path.exists(THAI_CSV):
        return {}
    df = pd.read_csv(THAI_CSV, encoding="utf-8-sig")
    table = {}
    for _, r in df.iterrows():
        entry = {
            "kcal": float(r["kcal_per_100g"]),
            "protein": float(r["protein_per_100g"]),
            "carbs": float(r["carbs_per_100g"]),
            "fat": float(r["fat_per_100g"]),
            "matched_name": str(r["name"]),
            "source": str(r.get("source", "ตารางอาหารไทย")),
        }
        aliases = [] if pd.isna(r.get("aliases")) else str(r["aliases"]).split("|")
        for k in [str(r["name"]), *aliases]:
            k = k.strip().lower()
            if k:
                table[k] = entry
    return table


def lookup_food(name_original: str, name_en: str) -> dict | None:
    """ค้นตารางอาหารไทยของคุณก่อน (ตรงชื่อ/ชื่อเรียกอื่นแบบเป๊ะ) ถ้าไม่เจอค่อยค้น USDA
    ไม่ใช้การจับคู่บางส่วน เพื่อไม่ให้ 'ข้าวผัดกะเพรา' ถูกจับเป็น 'ข้าวผัด'"""
    mtime = os.path.getmtime(THAI_CSV) if os.path.exists(THAI_CSV) else 0.0
    table = _load_thai_table(mtime)
    for n in (name_original, name_en):
        key = str(n or "").strip().lower()
        if key in table:
            return table[key]
    usda = lookup_per_100g(name_en)
    return {**usda, "source": "USDA"} if usda else None


def scale(per100: dict, grams: float) -> dict:
    f = grams / 100.0
    return {k: round(per100[k] * f, 1) for k in ("kcal", "protein", "carbs", "fat")}
