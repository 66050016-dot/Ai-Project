import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()

# ใช้รุ่น gemini-3.8-flash ตามที่ระบบ Google กำหนด
MODEL = "gemini-3.8-flash"

class FoodItem(BaseModel):
    name_original: str = Field(description="ชื่ออาหาร เช่น กล้วย, ข้าวผัด")
    grams: float = Field(description="น้ำหนักโดยประมาณเป็นกรัม เช่น 120")
    kcal: float = Field(description="แคลอรี่โดยประมาณ (kcal)")
    protein: float = Field(description="โปรตีน (กรัม)")
    carbs: float = Field(description="คาร์โบไฮเดรต (กรัม)")
    fat: float = Field(description="ไขมัน (กรัม)")
    meal: str = Field(description="breakfast, lunch, dinner หรือ snack")

class ParsedMeal(BaseModel):
    items: list[FoodItem]

IMAGE_PROMPT = """Analyze this food image. Identify the food item, estimate its weight in grams, and provide estimated nutrition values (kcal, protein, carbs, fat). Do not leave them as zero.
- name_original: ชื่ออาหารภาษาไทย
- grams: น้ำหนักกรัม
- kcal: พลังงาน (kcal)
- protein, carbs, fat: สารอาหาร
- meal: snack หรือมื้ออื่นๆ
"""

TEXT_PROMPT = """Extract food items and estimate nutrition values (grams, kcal, protein, carbs, fat).
User text: {text}
"""

def parse_food_text(text: str) -> list[FoodItem]:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("ไม่พบ GEMINI_API_KEY ในไฟล์ .env")
    
    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model=MODEL, 
        contents=TEXT_PROMPT.format(text=text), 
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ParsedMeal,
            temperature=0.2,
        )
    )
    return ParsedMeal.model_validate_json(response.text).items

def parse_food_image(image_bytes: bytes, mime_type: str) -> list[FoodItem]:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("ไม่พบ GEMINI_API_KEY ในไฟล์ .env")
    
    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            IMAGE_PROMPT
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ParsedMeal,
            temperature=0.2,
        )
    )
    return ParsedMeal.model_validate_json(response.text).items