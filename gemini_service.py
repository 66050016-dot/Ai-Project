import os
from google import genai
from dotenv import load_dotenv

load_dotenv() 

def ask_gemini(prompt: str, api_key: str | None = None, model: str = "gemini-3.8-flash") -> str:
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return "❌ ไม่พบ API Key กรุณาตรวจสอบไฟล์ .env"
        
    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text or "Gemini ไม่ได้ส่งข้อความตอบกลับ"
    except Exception as e:
        return f"❌ เกิดข้อผิดพลาดจาก Gemini API: {e}"