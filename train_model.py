import pandas as pd
import numpy as np
import psycopg2
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from os.path import join, dirname
import os
import joblib

connection = None
cursor = None

try:
    # Load environment variables
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)
    print("[1] Environment variables loaded successfully.")

    HOST = os.getenv("HOST")
    DATABASE = os.getenv("DATABASE")
    USER = os.getenv("USER")
    PASSWORD = os.getenv("PASSWORD")
    PORT = os.getenv("PORT")
    
    connection = psycopg2.connect(
        host=HOST,
        database=DATABASE,
        user=USER,
        password=PASSWORD,
        port=PORT
    )
    cursor = connection.cursor()
    print("[2] Connected to PostgreSQL database successfully.")

    # --- PHẦN 1: XỬ LÝ NHÀ HÀNG VÀ HUẤN LUYỆN MÔ HÌNH ---
    print("[3] Querying restaurants...")
    restaurant_query = """
        select b.restaurant_id, c.name as tag_name
        from restaurants a
        inner join restaurant_tags b on a.id = b.restaurant_id
        inner join tags c on c.id = b.tag_id
    """
    cursor.execute(restaurant_query)
    records_restaurant = cursor.fetchall()
    if len(records_restaurant) == 0:
         raise ValueError("No restaurant data fetched. Cannot train model.")
         
    df_restaurants = pd.DataFrame(records_restaurant, columns=[desc[0] for desc in cursor.description])
    print(df_restaurants.head(10))

    print("[4] Creating restaurant profiles...")
    restaurant_metrics = df_restaurants.groupby(["restaurant_id"])["tag_name"] \
                                       .apply(lambda x: ' | '.join(x)) \
                                       .reset_index(name="restaurantCharacteristics")
    
    print("[5] Training TF-IDF vectorizer on restaurants...")
    vectorizer = TfidfVectorizer()
    restaurant_vecs = vectorizer.fit_transform(restaurant_metrics["restaurantCharacteristics"])
    print("Vectorizer trained.")

    # LƯU MÔ HÌNH (Rất quan trọng cho api_server.py)
    MODEL_PATH = "/models/" # Lưu vào ổ cứng chung
    joblib.dump(vectorizer, MODEL_PATH + 'vectorizer.pkl')
    joblib.dump(restaurant_vecs, MODEL_PATH + 'restaurant_vectors.pkl')
    joblib.dump(restaurant_metrics, MODEL_PATH + 'restaurant_metrics.pkl')
    print("Saved vectorizer, restaurant vectors, and metrics to .pkl files.")


    # --- PHẦN 2: XỬ LÝ USER VÀ TẠO RECOMMENDATION HÀNG LOẠT ---
    print("[6] Querying users...")
    users_query = """
        select b.user_id, c.name as tag_name
        from users a
        inner join user_tags b on b.user_id = a.id
        inner join tags c on c.id = b.tag_id
    """
    cursor.execute(users_query)
    records_users = cursor.fetchall()
    
    if len(records_users) == 0:
        print("Warning: No user data fetched. Skipping batch recommendation.")
    else:
        df_users = pd.DataFrame(records_users, columns=[desc[0] for desc in cursor.description])
        print(df_users.head(10))
        
        print("[7] Creating user profiles...")
        user_metrics = df_users.groupby(["user_id"])["tag_name"] \
                               .apply(lambda x: " ".join(x)) \
                               .reset_index(name="userCharacteristics")
        
        print("[8] Transforming user profiles...")
        user_vecs = vectorizer.transform(user_metrics["userCharacteristics"])

        print("[9] Computing cosine similarity...")
        similarity = cosine_similarity(user_vecs, restaurant_vecs)
        
        print("[10] Generating all recommendations (small dataset)...")
        recommendations = []

        for user_idx, user_id in enumerate(user_metrics["user_id"]):
            for restaurant_idx, restaurant_id in enumerate(restaurant_metrics["restaurant_id"]):
                recommendations.append((
                    int(user_id),
                    int(restaurant_id),
                    float(similarity[user_idx, restaurant_idx])
                ))
                
        if not recommendations:
            print("No recommendations generated from user data.")
        else:
            df_recommendations = pd.DataFrame(recommendations, columns=["user_id", "restaurant_id", "score"])
            print("Sample Recommendation Data: ")
            print(df_recommendations.head(10))
            
            # --- PHẦN 3: CẬP NHẬT DATABASE ---
            print("[11] Deleting ALL existing recommendations...")
            cursor.execute("TRUNCATE TABLE recommendation RESTART IDENTITY;")
            print("Truncated recommendation table.")
            
            print("[12] Inserting new recommendations...")
            insert_query = "INSERT INTO recommendation (user_id, restaurant_id, score) VALUES %s"
            execute_values(cursor, insert_query, df_recommendations.values.tolist())
            print(f"Inserted {len(df_recommendations)} recommendations into DB")

    connection.commit()
    print("All changes committed to the database.")
    print("BATCH recommendation process completed successfully.")

except Exception as e:
    print(f"Error: {e}")
    if connection:
        connection.rollback()
        print("Transaction rolled back due to error.")
    raise e
finally:
    print("--- Cleaning up resources ---")
    if cursor:
        cursor.close()
        print("Cursor closed.")
    if connection:
        connection.close()
        print("PostgreSQL connection closed.")