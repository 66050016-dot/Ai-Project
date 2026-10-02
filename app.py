import streamlit as st
import pandas as pd
from gemini_service import ask_gemini
from ml_tools import analyze_health_factors
from datetime import date
from food_tab import render_food_log_tab
from trends_tab import render_trends_tab
import database as db
from stats import protein_guideline, build_summary
import json

st.set_page_config(page_title="AI Health Coach Pro", page_icon="💪", layout="wide")
st.title("💪 AI Health Coach & Data Analytics")
st.markdown("ระบบวิเคราะห์ข้อมูลทางสรีรวิทยาด้วย **Machine Learning** และจัดตารางโดย **Generative AI (Gemini)**")

@st.cache_data
def load_data():
    try:
        # อ่านไฟล์ Dataset ของจริงจาก Kaggle
        return pd.read_csv("gym_members_exercise_tracking.csv")
    except FileNotFoundError:
        st.error("❌ ไม่พบไฟล์ 'gym_members_exercise_tracking.csv' กรุณาตรวจสอบให้แน่ใจว่าไฟล์อยู่ในโฟลเดอร์เดียวกับโค้ด")
        return None

df = load_data()

# แถบด้านข้างสำหรับกรอกข้อมูล
with st.sidebar:
    st.header("👤 ข้อมูลทางสรีรวิทยา")
    gender = st.selectbox("เพศ", ["ชาย", "หญิง"])
    age = st.number_input("อายุ (ปี)", min_value=15, max_value=80, value=22)
    weight = st.number_input("น้ำหนัก (กก.)", min_value=30.0, max_value=150.0, value=65.0)
    height = st.number_input("ส่วนสูง (ซม.)", min_value=140.0, max_value=200.0, value=170.0)
    
    activity_levels = {
        "นั่งทำงานเป็นหลัก (ไม่ออกกำลังกาย)": 1.2,
        "ขยับตัวบ้าง (ออกกำลังกาย 1-3 วัน/สัปดาห์)": 1.375,
        "ปานกลาง (ออกกำลังกาย 3-5 วัน/สัปดาห์)": 1.55,
        "แอคทีฟมาก (ออกกำลังกาย 6-7 วัน/สัปดาห์)": 1.725
    }
    activity = st.selectbox("ระดับกิจกรรม", list(activity_levels.keys()))
    goal = st.selectbox("เป้าหมายของคุณ", ["ลดน้ำหนัก", "รักษาน้ำหนัก", "เพิ่มกล้ามเนื้อ"])

# คำนวณค่าสุขภาพทางคณิตศาสตร์ 
bmi = weight / ((height / 100) ** 2)
if gender == "ชาย":
    bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
else:
    bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161

tdee = bmr * activity_levels[activity]

if goal == "ลดน้ำหนัก":
    target_cal = tdee - 500
elif goal == "เพิ่มกล้ามเนื้อ":
    target_cal = tdee + 300
else:
    target_cal = tdee

# สร้างฐานข้อมูล และบันทึกข้อมูล/เป้าหมายของวันนี้
db.init_db()
db.save_profile(date.today(), gender, age, weight, height, activity, goal, target_cal)
protein_target = protein_guideline(weight, goal)

tab1, tab2, tab3, tab4 = st.tabs([
    "🤖 โค้ชสุขภาพ AI (Personalized Plan)",
    "📊 วิเคราะห์สถิติคนเข้าฟิตเนส (Data Analytics)",
    "🍽️ บันทึกอาหาร",
    "📈 แนวโน้มของฉัน",
])

with tab3:
    render_food_log_tab(target_cal)

with tab4:
    render_trends_tab(target_cal, goal, weight, protein_target)

with tab1:
    st.subheader("🎯 ข้อมูลทางสรีรวิทยาและการเผาผลาญ")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("BMI (ดัชนีมวลกาย)", f"{bmi:.1f}")
    col2.metric("BMR (พลังงานพื้นฐาน)", f"{bmr:.0f} kcal")
    col3.metric("TDEE (พลังงานที่ใช้จริง)", f"{tdee:.0f} kcal")
    col4.metric("เป้าหมายแคลอรี่/วัน", f"{target_cal:.0f} kcal", goal)

    st.divider()
    use_history = st.checkbox("📊 ให้โค้ชใช้ข้อมูลที่ฉันบันทึกไว้ (14 วันล่าสุด) ในการปรับแผน", value=True)
    if st.button("✨ ให้ AI จัดสัดส่วนสารอาหารและตารางออกกำลังกาย", type="primary"):
        with st.spinner("AI กำลังวิเคราะห์ข้อมูลของคุณ (ใช้เวลาเพียง 1-3 วินาที)..."):
            history_block = ""
            if use_history:
                hist = build_summary(14, target_cal, protein_target, goal)
                if hist["days_logged"] >= 3:
                    history_block = (
                        "\n            ข้อมูลที่ผู้ใช้บันทึกจริงย้อนหลัง (คำนวณแล้ว ใช้เฉพาะตัวเลขนี้ ห้ามแต่งตัวเลขเพิ่ม):\n"
                        + json.dumps(hist, ensure_ascii=False)
                        + "\n            ให้ปรับสัดส่วนอาหารและแผนออกกำลังกายโดยอ้างอิงพฤติกรรมจริงนี้ เช่น จุดที่ทำได้ดีและจุดที่ควรปรับ\n"
                    )
                else:
                    st.info("ข้อมูลที่บันทึกยังน้อยกว่า 3 วัน จึงสร้างแผนจากข้อมูลร่างกายอย่างเดียวก่อน")
            
            # Prompt สำหรับส่งให้ Gemini
            prompt = f"""
            คุณเป็นผู้เชี่ยวชาญด้านโภชนาการและเทรนเนอร์ฟิตเนสระดับมืออาชีพ ตอบเป็นภาษาไทยให้อ่านง่าย จัดหน้าสวยงาม
            ข้อมูลผู้ใช้: เพศ{gender} อายุ {age} ปี เป้าหมายคือ {goal}
            ค่า BMI = {bmi:.1f}, BMR = {bmr:.0f} kcal, พลังงานที่ต้องการต่อวัน = {target_cal:.0f} kcal
            {history_block}
            1. ช่วยแจกแจงสัดส่วน Macronutrients (โปรตีน, คาร์บ, ไขมัน) เป็นกรัม ให้พอดีกับเป้าหมาย {target_cal:.0f} kcal
            2. ออกแบบตารางอาหาร 1 วันที่สอดคล้องกับสัดส่วนด้านบน
            3. แนะนำตารางออกกำลังกายที่เหมาะกับระดับกิจกรรม '{activity}'
            """
            
            # กำหนด model="gemini-3.8-flash" ให้ตรงกับระบบปัจจุบัน
            reply = ask_gemini(prompt, model="gemini-3.8-flash")
            st.success("✅ โค้ช AI จัดตารางเสร็จสิ้น!")
            st.markdown(reply)

with tab2:
    st.subheader("📈 วิเคราะห์สถิติข้อมูลของจริง (Gym Members Dataset)")
    st.write("โมเดล Machine Learning วิเคราะห์ว่า **ปัจจัยใดมีความสำคัญต่อการเผาผลาญแคลอรี่มากที่สุด**")
    
    if df is not None:
        r2, fig = analyze_health_factors(df)
        
        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.info(f"**ความน่าเชื่อถือของโมเดล (R-Squared):** {r2*100:.2f}%")
            st.write("**Insight (ข้อค้นพบ):**")
            st.write("จากข้อมูลจริงพบว่า 'เวลาที่ใช้ในการออกกำลังกาย (ชั่วโมง)' มีผลต่อการเผาผลาญพลังงานมากกว่าน้ำหนักตัวหรืออายุเสียอีก")
            with st.expander("ดูชุดข้อมูลดิบของจริง (10 แถวแรก)"):
                st.dataframe(df.head(10))
                
        with col_b:
            st.plotly_chart(fig, use_container_width=True)