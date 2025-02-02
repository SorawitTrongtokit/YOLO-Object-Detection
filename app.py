import streamlit as st
from ultralytics import YOLO
import os
import psycopg2
from dotenv import load_dotenv

# โหลด environment variables จากไฟล์.env
load_dotenv()

# เชื่อมต่อกับฐานข้อมูล PostgreSQL (เหมือนเดิม)
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST'),
            database=os.environ.get('DB_NAME'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD')
        )
        return conn
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        return None

# โหลดโมเดล YOLOv8 (เหมือนเดิม)
model_path = os.environ.get('MODEL_PATH', 'model/best.pt')
try:
    model = YOLO(model_path)
    print("YOLOv8 model loaded successfully!")
except Exception as e:
    print(f"Error loading YOLOv8 model: {e}")
    exit()

# ฟังก์ชันสำหรับดึงราคาจากฐานข้อมูล (เหมือนเดิม)
def get_price(product_name):
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute("SELECT price FROM products WHERE name = %s", (product_name,))
        price = cur.fetchone()
        return float(price) if price else None
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if conn:
            conn.close()

# Streamlit app
st.title('Image Price Checker')

uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
if uploaded_file is not None:
    # บันทึกไฟล์ภาพ
    #  ตรวจสอบว่ามีโฟลเดอร์ temp หรือไม่  ถ้าไม่มีให้สร้าง
    if not os.path.exists("temp"):
        os.makedirs("temp")
    image_path = os.path.join("temp", uploaded_file.name)
    with open(image_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # ประมวลผลภาพ
    results = model(image_path)
    prices =
    for result in results:
        for box in result.boxes.data.tolist():
            x1, y1, x2, y2, confidence, class_id = box
            product_name = result.names[int(class_id)]
            price = get_price(product_name)
            if price:
                prices.append({'product': product_name, 'price': price})

    # แสดงผลลัพธ์
    if prices:
        st.success("Found these products:")
        for item in prices:
            st.write(f"{item['product']}: {item['price']} บาท")
    else:
        st.warning("No products found in the image.")

    # ลบไฟล์ภาพ
    os.remove(image_path)