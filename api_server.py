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

print("--- STARTING RECOMMENDATION SERVER ---")

# Đọc MODEL_PATH từ env, mặc định /data (phù hợp khi mount volume trên Railway)
MODEL_PATH = os.getenv("MODEL_PATH", "/models/")
MODEL_PATH = MODEL_PATH if MODEL_PATH.endswith("/") else MODEL_PATH + "/"

try:
    print(f"[1] Loading model from .pkl files at: {MODEL_PATH}")
    vectorizer = joblib.load(os.path.join(MODEL_PATH, 'vectorizer.pkl'))
    restaurant_vecs = joblib.load(os.path.join(MODEL_PATH, 'restaurant_vectors.pkl'))
    restaurant_metrics = joblib.load(os.path.join(MODEL_PATH, 'restaurant_metrics.pkl'))
except FileNotFoundError:
    print(f"Error: cannot find model files in '{MODEL_PATH}'.")
    try:
        print(f"Files in {MODEL_PATH}: {os.listdir(MODEL_PATH)}")
    except Exception:
        print(f"Cannot list directory {MODEL_PATH}. It may not exist or is not mounted.")
    exit(1)

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
    Call this API to generate recommendations for a new user.
    """
    print(f"\n[API] received the request for user_id: {user_id}")
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
        print("[API] Connected to DB.")

        # 2. Query CHỈ user mới
        print(f"[API] Querying tags for user_id: {user_id}")
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
            print(f"[API] No tags found for user_id: {user_id}")
            return jsonify({"status": "error", "message": "User has no tags"}), 404

        df_user = pd.DataFrame(records_user, columns=['user_id', 'tag_name'])
        print("[API] Sample tags of the user:")
        print(df_user.head(10))
        
        # 3. Create User Profile
        user_profile_text = ' '.join(df_user['tag_name'].tolist())
        print(f"[API] User profile text: '{user_profile_text}'")

        # 4. Use model (in RAM)
        user_vec = vectorizer.transform([user_profile_text])
        similarity_scores = cosine_similarity(user_vec, restaurant_vecs)
        # user_scores is an array (e.g.: [0.1, 0.5, 0.0, ...])
        user_scores = similarity_scores[0] 

        # --- FIX: REPLACE TOP-K WITH LOOP THROUGH ALL ---
        print("[API] Generating all recommendations (small dataset)...")
        recommendations = []

        # Loop through all restaurants (from 'restaurant_metrics' loaded)
        for restaurant_idx, restaurant_id in enumerate(restaurant_metrics["restaurant_id"]):
            recommendations.append((
                int(user_id),
                int(restaurant_id),
                float(user_scores[restaurant_idx]) # score
            ))
        # --- END FIX ---

        if not recommendations:
             print(f"[API] No recommendations generated for user_id: {user_id}")
             return jsonify({"status": "ok", "message": "No recommendations generated"}), 200
        else:
            df_recommendations = pd.DataFrame(recommendations, columns=["user_id", "restaurant_id", "score"])
            print("[API] Sample recommendations generated:")
            print(df_recommendations.head(10))

        # 7. Save to DB
        print(f"[API] Preparing to save {len(recommendations)} recommendations to DB...")
        cursor.execute("DELETE FROM recommendation WHERE user_id = %s", (user_id,))
        
        insert_query = "INSERT INTO recommendation (user_id, restaurant_id, score) VALUES %s"
        execute_values(cursor, insert_query, recommendations)
        
        connection.commit()
        print(f"[API] Successfully saved {len(recommendations)} recommendations for user_id: {user_id}")
        
        return jsonify({
            "status": "success",
            "user_id": user_id,
            "generated_count": len(recommendations)
        }), 200

    except Exception as e:
        print(f"[API] ERROR: {e}")
        if connection:
            connection.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            print("[API] Closed DB connection.")