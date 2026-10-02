from datetime import date
import pandas as pd
import streamlit as st

import database as db
from food_parser import parse_food_image, parse_food_text

MEAL_TH = {"breakfast": "เช้า", "lunch": "กลางวัน", "dinner": "เย็น", "snack": "ของว่าง"}

def _to_draft(items, meal_override: str | None = None) -> list[dict]:
    return [
        {
            "อาหาร": it.name_original,
            "กรัม": it.grams,
            "kcal": it.kcal,
            "protein": it.protein,
            "carbs": it.carbs,
            "fat": it.fat,
            "มื้อ": meal_override or (it.meal if it.meal in MEAL_TH else "snack"),
        }
        for it in items
    ]

def render_food_log_tab(target_cal: float):
    st.subheader("🍽️ บันทึกอาหาร")
    st.caption("AI ช่วยวิเคราะห์รายการอาหาร น้ำหนัก และประเมินสารอาหาร/แคลอรี่ให้คุณอัตโนมัติ")

    if "draft" not in st.session_state:
        st.session_state.draft = None

    day = st.date_input("วันที่", value=date.today(), max_value=date.today())
    mode = st.radio("วิธีบันทึก", ["✍️ พิมพ์", "📷 ถ่ายรูป/อัปโหลดรูป"], horizontal=True)

    if mode.startswith("✍️"):
        text = st.text_area(
            "วันนี้กินอะไรบ้าง?",
            placeholder="เช่น ข้าวผัดกะเพราไข่ดาว 1 จาน กับชาเย็น 1 แก้วตอนเที่ยง",
        )
        if st.button("วิเคราะห์", type="primary", disabled=not text.strip()):
            with st.spinner("AI กำลังวิเคราะห์และคำนวณสารอาหาร..."):
                try:
                    st.session_state.draft = _to_draft(parse_food_text(text))
                except Exception as e:
                    st.error(f"❌ วิเคราะห์ไม่สำเร็จ: {e}")
    else:
        photo = st.file_uploader("รูปอาหาร", type=["jpg", "jpeg", "png", "webp"])
        meal_pick = st.selectbox("มื้อนี้คือ", list(MEAL_TH), index=1, format_func=lambda m: MEAL_TH[m])
        if photo is not None:
            st.image(photo, width=280)
        if st.button("สแกนรูป", type="primary", disabled=photo is None):
            with st.spinner("AI กำลังตรวจดูรูปและประเมินแคลอรี่..."):
                try:
                    items = parse_food_image(photo.getvalue(), photo.type or "image/jpeg")
                    if not items:
                        st.warning("ไม่พบอาหารในรูป ลองถ่ายใหม่ให้เห็นจานชัดขึ้น")
                    st.session_state.draft = _to_draft(items, meal_override=meal_pick) if items else None
                except Exception as e:
                    st.error(f"❌ สแกนรูปไม่สำเร็จ: {e}")
        st.caption("⚠️ ปริมาณและแคลอรี่มาจากการประเมินของ AI สามารถแก้ไขตัวเลขในตารางได้ก่อนบันทึก")

    draft = st.session_state.draft
    if draft:
        st.markdown("**ตรวจสอบก่อนบันทึก** (แก้ไขชื่อ, กรัม หรือแคลอรี่ได้ตามต้องการ)")
        edited = st.data_editor(
            pd.DataFrame(draft), use_container_width=True, num_rows="dynamic", key="editor",
            column_config={"มื้อ": st.column_config.SelectboxColumn(options=list(MEAL_TH))},
        )

        computed = []
        total = {"kcal": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
        for _, row in edited.iterrows():
            name = str(row.get("อาหาร") or "").strip()
            if not name:
                continue
            item_data = {
                "อาหาร": name,
                "กรัม": float(row.get("กรัม", 0)),
                "kcal": float(row.get("kcal", 0)),
                "protein": float(row.get("protein", 0)),
                "carbs": float(row.get("carbs", 0)),
                "fat": float(row.get("fat", 0)),
                "มื้อ": row["มื้อ"],
                "แหล่งข้อมูล": "AI ประเมิน"
            }
            computed.append(item_data)
            for k in total:
                total[k] += item_data[k]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("พลังงานรวม", f"{total['kcal']:.0f} kcal")
        c2.metric("โปรตีน", f"{total['protein']:.0f} g")
        c3.metric("คาร์บ", f"{total['carbs']:.0f} g")
        c4.metric("ไขมัน", f"{total['fat']:.0f} g")

        if computed and st.button("✅ บันทึกมื้อนี้"):
            n = db.add_foods(computed, day)
            st.session_state.draft = None
            st.success(f"บันทึกแล้ว {n} รายการ")
            st.rerun()

    log = db.get_foods(day, day)
    if not log.empty:
        st.divider()
        st.markdown(f"### สรุปวันที่ {day.strftime('%d/%m/%Y')}")
        eaten = log["kcal"].fillna(0).sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("กินไปแล้ว", f"{eaten:.0f} kcal")
        m2.metric("เป้าหมาย", f"{target_cal:.0f} kcal")
        m3.metric("คงเหลือ", f"{target_cal - eaten:.0f} kcal")
        st.progress(min(max(eaten / target_cal, 0.0), 1.0))

        show = log[["id", "meal", "name", "grams", "kcal", "protein", "carbs", "fat"]]
        st.dataframe(show, use_container_width=True, hide_index=True)

        to_delete = st.multiselect(
            "เลือกรายการที่จะลบ (ตาม id)", log["id"].tolist(),
            format_func=lambda i: f"{i}: {log.loc[log['id'] == i, 'name'].iloc[0]}",
        )
        if to_delete and st.button("🗑️ ลบรายการที่เลือก"):
            db.delete_foods(to_delete)
            st.rerun()