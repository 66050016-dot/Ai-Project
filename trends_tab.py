import json
from datetime import date, timedelta

import plotly.graph_objects as go
import streamlit as st

import database as db
import stats
from ai_coach import analyze_week


def render_trends_tab(target_cal: float, goal: str, weight_now: float, protein_target: float):
    st.subheader("📈 แนวโน้มของคุณ")
    today = date.today()

    # ---- บันทึกด่วน: น้ำหนัก / น้ำดื่ม ----
    c1, c2 = st.columns(2)
    with c1:
        w = st.number_input("น้ำหนักวันนี้ (กก.)", min_value=20.0, max_value=300.0,
                            value=float(weight_now), step=0.1, key="w_input")
        if st.button("บันทึกน้ำหนัก"):
            db.set_weight(today, w)
            st.rerun()
    with c2:
        today_water = db.get_water(today, today)
        liters = float(today_water["liters"].iloc[0]) if not today_water.empty else 0.0
        st.metric("น้ำที่ดื่มวันนี้", f"{liters:.2f} L")
        b1, b2, b3 = st.columns(3)
        if b1.button("+0.25"):
            db.add_water(today, 0.25); st.rerun()
        if b2.button("+0.5"):
            db.add_water(today, 0.5); st.rerun()
        if b3.button("รีเซ็ต"):
            db.set_water(today, 0.0); st.rerun()

    st.divider()

    days = st.radio("ช่วงเวลา", [7, 14, 30], horizontal=True,
                    format_func=lambda d: f"{d} วัน")
    df = stats.daily_table(today - timedelta(days=days - 1), today)
    logged = df[df["logged"]]

    if logged.empty:
        st.info("ยังไม่มีข้อมูลในช่วงนี้ ไปบันทึกอาหารที่แท็บ 🍽️ ก่อนนะ")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("เฉลี่ย kcal/วัน", f"{logged['kcal'].mean():.0f}", f"เป้า {target_cal:.0f}", delta_color="off")
        m2.metric("เฉลี่ยโปรตีน", f"{logged['protein'].mean():.0f} g", f"เป้า ~{protein_target:.0f}", delta_color="off")
        m3.metric("วันที่บันทึก", f"{len(logged)}/{days}")
        m4.metric("🔥 Streak", f"{stats.current_streak()} วัน")

        # กราฟ 1: แคลอรี่รายวันแยกตามสารอาหาร เทียบเป้า
        fig = go.Figure()
        fig.add_bar(x=df["day"], y=df["protein"] * 4, name="โปรตีน", marker_color="#16a34a")
        fig.add_bar(x=df["day"], y=df["carbs"] * 4, name="คาร์บ", marker_color="#eab308")
        fig.add_bar(x=df["day"], y=df["fat"] * 9, name="ไขมัน", marker_color="#f97316")
        fig.add_hline(y=target_cal, line_dash="dash", line_color="#334155",
                      annotation_text=f"เป้าหมาย {target_cal:.0f}")
        fig.update_layout(barmode="stack", title="แคลอรี่รายวัน (แยกตามสารอาหาร)",
                          yaxis_title="kcal", legend_orientation="h", height=380)
        st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        wdf = df.dropna(subset=["weight"])
        if len(wdf) >= 1:
            f = go.Figure(go.Scatter(x=wdf["day"], y=wdf["weight"], mode="lines+markers",
                                     line_color="#0ea5e9"))
            f.update_layout(title="น้ำหนัก (กก.)", height=300)
            st.plotly_chart(f, use_container_width=True)
        else:
            st.caption("ยังไม่มีข้อมูลน้ำหนักในช่วงนี้")
    with col_b:
        wa = df.dropna(subset=["water"])
        if len(wa) >= 1:
            f = go.Figure(go.Bar(x=wa["day"], y=wa["water"], marker_color="#38bdf8"))
            f.update_layout(title="น้ำดื่ม (ลิตร)", height=300)
            st.plotly_chart(f, use_container_width=True)
        else:
            st.caption("ยังไม่มีข้อมูลน้ำดื่มในช่วงนี้")

    # ---- AI วิเคราะห์ ----
    st.divider()
    st.markdown("### 🤖 ให้ AI วิเคราะห์ข้อมูลของคุณ")
    if st.button("✨ วิเคราะห์ช่วงนี้", type="primary"):
        summary = stats.build_summary(days, target_cal, protein_target, goal)
        with st.spinner("AI กำลังวิเคราะห์..."):
            reply = analyze_week(summary)
        st.markdown(reply)
        with st.expander("ดูข้อมูลสรุปที่ส่งให้ AI (ไม่ส่งชื่อหรือข้อมูลดิบ)"):
            st.code(json.dumps(summary, ensure_ascii=False, indent=2), language="json")
        st.caption("⚠️ คำแนะนำทั่วไป ไม่ใช่คำแนะนำทางการแพทย์ หากมีโรคประจำตัวควรปรึกษาแพทย์หรือนักกำหนดอาหาร")

    # ---- ส่งออกข้อมูล (CSV เปิดใน Excel ได้ ภาษาไทยไม่เพี้ยน) ----
    st.divider()
    st.markdown("### 📤 ส่งออกข้อมูล")
    e1, e2 = st.columns(2)
    all_foods = db.get_foods(date(2000, 1, 1), today)
    daily_all = stats.daily_table(today - timedelta(days=days - 1), today)
    e1.download_button(
        f"ดาวน์โหลดสรุปรายวัน ({days} วัน)",
        daily_all.to_csv(index=False).encode("utf-8-sig"),
        file_name="daily_summary.csv", mime="text/csv",
    )
    e2.download_button(
        "ดาวน์โหลดบันทึกอาหารทั้งหมด",
        all_foods.to_csv(index=False).encode("utf-8-sig"),
        file_name="food_log.csv", mime="text/csv", disabled=all_foods.empty,
    )
