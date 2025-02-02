import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from dotenv import load_dotenv
from ultralytics import YOLO

# โหลด environment variables จากไฟล์ .env
load_dotenv()

# สร้าง Flask application
app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_default_secret_key')

# กำหนด path สำหรับอัปโหลดไฟล์
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# เชื่อมต่อกับฐานข้อมูล PostgreSQL
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

# โหลดโมเดล YOLOv8
model_path = os.environ.get('MODEL_PATH', 'model/best.pt')
try:
    model = YOLO(model_path)
    print("YOLOv8 model loaded successfully!")
except Exception as e:
    print(f"Error loading YOLOv8 model: {e}")
    exit()

# ฟังก์ชันสำหรับดึงราคาจากฐานข้อมูล
def get_price(product_name):
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute("SELECT price FROM products WHERE name = %s", (product_name,))
        price = cur.fetchone()
        return float(price[0]) if price else None
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if conn:
            conn.close()

# API endpoint สำหรับรับภาพและประมวลผล
@app.route('/api/process', methods=['POST'])
def process_image_api():
    try:
        # ตรวจสอบว่ามีไฟล์ภาพถูกส่งมาหรือไม่
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'No image file found'})

        image_file = request.files['image']

        # ตรวจสอบว่าผู้ใช้เลือกไฟล์หรือไม่
        if image_file.filename == '':
            return jsonify({'success': False, 'message': 'No selected file'})

        # ตรวจสอบนามสกุลไฟล์
        allowed_extensions = {'png', 'jpg', 'jpeg'}
        file_extension = image_file.filename.split('.')[-1].lower()
        if '.' not in image_file.filename or file_extension not in allowed_extensions:
            return jsonify({'success': False, 'message': 'Invalid file type. Only PNG, JPG, and JPEG are allowed.'})

        # บันทึกไฟล์ภาพ
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_file.filename)
        image_file.save(image_path)

        # ประมวลผลภาพด้วย YOLOv8
        results = model(image_path)
        prices = []

        # วนลูปผ่านผลลัพธ์
        for result in results:
            for box in result.boxes.data.tolist():
                x1, y1, x2, y2, confidence, class_id = box
                product_name = result.names[int(class_id)]
                price = get_price(product_name)
                if price:
                    prices.append({'product': product_name, 'price': price})

        # ลบไฟล์ภาพหลังจากประมวลผลเสร็จสิ้น
        if os.path.exists(image_path):
            os.remove(image_path)

        # ส่งผลลัพธ์กลับเป็น JSON
        return jsonify({'success': True, 'prices': prices})

    except Exception as e:
        # ลบไฟล์ภาพหากเกิดข้อผิดพลาด
        if 'image_path' in locals() and os.path.exists(image_path):
            os.remove(image_path)
        return jsonify({'success': False, 'message': str(e)})

# รัน Flask application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)