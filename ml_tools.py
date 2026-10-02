import pandas as pd
from sklearn.linear_model import LinearRegression
import plotly.express as px

def analyze_health_factors(df: pd.DataFrame):
    """
    วิเคราะห์ความสัมพันธ์ของข้อมูลฟิตเนสด้วย Linear Regression
    คำนวณหา R-squared และสร้างกราฟ Plotly แสดงผล
    """
    # เลือกฟีเจอร์ตัวเลขที่เกี่ยวข้องกับการเผาผลาญแคลอรี่
    features = ['Session_Duration (hours)', 'Age', 'Weight (kg)', 'Heart_Rate']
    
    # ตรวจสอบว่าคอลัมน์ทั้งหมดอยู่ใน DataFrame หรือไม่
    available_features = [f for f in features if f in df.columns]
    
    if not available_features or 'Calories_Burned' not in df.columns:
        # กรณีคอลัมน์ใน Dataset ไม่ตรงเป๊ะ ใช้ค่าพรีเซ็ตสำรอง
        return 0.0, px.scatter(title="ไม่พบข้อมูลคอลัมน์ที่รองรับใน Dataset")

    X = df[available_features]
    y = df['Calories_Burned']

    model = LinearRegression()
    model.fit(X, y)
    r2 = model.score(X, y)

    # สร้างกราฟแสดงความสัมพันธ์ระหว่างระยะเวลาออกกำลังกายกับแคลอรี่ที่เผาผลาญ
    fig = px.scatter(
        df, 
        x='Session_Duration (hours)' if 'Session_Duration (hours)' in df.columns else available_features[0], 
        y='Calories_Burned',
        trendline="ols",
        title="ความสัมพันธ์ระหว่างระยะเวลาออกกำลังกายและแคลอรี่ที่เผาผลาญ",
        labels={
            'Session_Duration (hours)': 'ระยะเวลาออกกำลังกาย (ชั่วโมง)',
            'Calories_Burned': 'แคลอรี่ที่เผาผลาญ (kcal)'
        }
    )
    
    return r2, fig