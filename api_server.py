import pandas as pd
import numpy as np
import psycopg2
from sklearn.metrics.pairwise import cosine_similarity
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from os.path import join, dirname
import os
import joblib
from flask import Flask, jsonify, request

print("--- KHỞI ĐỘNG SERVER GỢI Ý ---")

try:
    print("[1] Đang tải mô hình từ file .pkl...")
    vectorizer = joblib.load('vectorizer.pkl')
    restaurant_vecs = joblib.load('restaurant_vectors.pkl')
    restaurant_metrics = joblib.load('restaurant_metrics.pkl')
    print("[2] Tải mô hình thành công, sẵn sàng hoạt động!")
except FileNotFoundError:
    print("LỖI: Không tìm thấy file .pkl...")
    exit()

# --- LOAD BIẾN MÔI TRƯỜNG CHO DB ---
load_dotenv(join(dirname(__file__), '.env')) 
HOST = os.getenv("HOST")
DATABASE = os.getenv("DATABASE")
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
PORT = os.getenv("PORT")

# --- KHỞI TẠO APP FLASK ---
app = Flask(__name__)

# --- TẠO ENDPOINT API ---
@app.route("/generate-recommendations/<int:user_id>", methods=["POST"])
def generate_for_new_user(user_id):
    """
    Tính toán và lưu recommendations cho 1 user_id cụ thể.
    """
    print(f"\n[API] Nhận được yêu cầu tính toán cho user_id: {user_id}")
    connection = None
    cursor = None
    try:
        # 1. Kết nối DB
        connection = psycopg2.connect(
            host=HOST,
            database=DATABASE, 
            user=USER, 
            password=PASSWORD,
            port=PORT
        )
        cursor = connection.cursor()
        print("[API] Đã kết nối DB.")

        # 2. Query CHỈ user mới
        print(f"[API] Querying tags cho user_id: {user_id}")
        user_query = """
            select b.user_id, c.name as tag_name
            from users a
            inner join user_tags b on b.user_id = a.id
            inner join tags c on c.id = b.tag_id
            WHERE a.id = %s
        """
        cursor.execute(user_query, (user_id,))
        records_user = cursor.fetchall()
        
        if len(records_user) == 0:
            print(f"[API] Không tìm thấy tag cho user_id: {user_id}")
            return jsonify({"status": "error", "message": "User has no tags"}), 404

        df_user = pd.DataFrame(records_user, columns=['user_id', 'tag_name'])
        
        # 3. Tạo Profile User
        user_profile_text = ' '.join(df_user['tag_name'].tolist())
        print(f"[API] Profile text của user: '{user_profile_text}'")

        # 4. Sử dụng mô hình (trong RAM)
        user_vec = vectorizer.transform([user_profile_text])
        similarity_scores = cosine_similarity(user_vec, restaurant_vecs)
        # user_scores là một mảng (ví dụ: [0.1, 0.5, 0.0, ...])
        user_scores = similarity_scores[0] 

        # --- SỬA LỖI: THAY THẾ TOP-K BẰNG VÒNG LẶP TẤT CẢ ---
        print("[API] Generating all recommendations (small dataset)...")
        recommendations = []

        # Lặp qua tất cả nhà hàng (từ 'restaurant_metrics' đã tải)
        for restaurant_idx, restaurant_id in enumerate(restaurant_metrics["restaurant_id"]):
            recommendations.append((
                int(user_id),
                int(restaurant_id),
                float(user_scores[restaurant_idx]) # Lấy điểm của nhà hàng này
            ))
        # --- KẾT THÚC SỬA LỖI ---
        
        if not recommendations:
             print(f"[API] Không tạo được recommendation nào cho user_id: {user_id}")
             return jsonify({"status": "ok", "message": "No recommendations generated"}), 200

        # 7. Lưu vào DB
        print(f"[API] Chuẩn bị lưu {len(recommendations)} recommendations vào DB...")
        cursor.execute("DELETE FROM recommendation WHERE user_id = %s", (user_id,))
        
        insert_query = "INSERT INTO recommendation (user_id, restaurant_id, score) VALUES %s"
        execute_values(cursor, insert_query, recommendations)
        
        connection.commit()
        print(f"[API] THÀNH CÔNG! Đã lưu {len(recommendations)} recommendations cho user_id: {user_id}")
        
        return jsonify({
            "status": "success",
            "user_id": user_id,
            "generated_count": len(recommendations)
        }), 200

    except Exception as e:
        print(f"[API] LỖI: {e}")
        if connection:
            connection.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            print("[API] Đã đóng kết nối DB.")