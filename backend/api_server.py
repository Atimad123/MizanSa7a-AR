from __future__ import annotations
import logging
import argparse
from datetime import datetime, timedelta
from functools import wraps

import jwt
import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS

from config import Config
from postgres_client import db
from meal_analyzer import analyze_meal
from user_manager import user_manager
from history_db import add_meal, get_history, delete_meal, clear_history, get_stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s – %(message)s")
log = logging.getLogger("NutriVoice.API")

app = Flask(__name__, static_folder=".")
app.config["SECRET_KEY"] = Config.SECRET_KEY
CORS(app, resources={r"/api/*": {"origins": "*"}})

def _make_token(user: dict) -> str:
    payload = {
        "user_id":  user["id"],
        "username": user["username"],
        "email":    user["email"],
        "exp": datetime.utcnow() + timedelta(days=Config.JWT_EXPIRY_DAYS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "")
        if token.startswith("Bearer "):
            token = token[7:]
        if not token:
            return jsonify({"status": "error", "error": "Token manquant"}), 401
        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            request.current_user = data
        except jwt.ExpiredSignatureError:
            return jsonify({"status": "error", "error": "Token expiré"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"status": "error", "error": "Token invalide"}), 401
        return f(*args, **kwargs)
    return decorated

def optional_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "")
        if token.startswith("Bearer "):
            token = token[7:]
        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            request.current_user = data
        except Exception:
            request.current_user = None
        return f(*args, **kwargs)
    return decorated

# ==================== PAGES STATIQUES ====================
@app.route("/")
def home():
    return redirect("/login")

@app.route("/login")
def login_page():
    return send_from_directory(".", "login.html")

@app.route("/index")
def index_page():
    return send_from_directory(".", "index.html")

@app.route("/stats")
def stats_page():
    return send_from_directory(".", "stats.html")

@app.route("/profile")
def profile_page():
    return send_from_directory(".", "profile.html")

# ==================== API ====================
@app.route("/api/status")
def status():
    return jsonify({"status": "success", "app": Config.APP_NAME, "version": Config.VERSION, "db": db.status()})

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json or {}
    res = user_manager.register(data.get("username",""), data.get("email",""), data.get("password",""))
    if res["status"] == "success":
        token = _make_token(res["user"])
        return jsonify({"status": "success", "token": token, "user": res["user"]}), 201
    return jsonify(res), 400

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json or {}
    res = user_manager.login(data.get("email",""), data.get("password",""))
    if res["status"] == "success":
        token = _make_token(res["user"])
        return jsonify({"status": "success", "token": token, "user": res["user"]})
    return jsonify(res), 401

@app.route("/api/auth/me", methods=["GET"])
@token_required
def me():
    return jsonify({"status": "success", "user": request.current_user})

@app.route("/api/analyze", methods=["POST"])
@optional_auth
def analyze_meal_route():
    data = request.json or {}
    text = data.get("text", "").strip()
    method = data.get("method", "normalizer")
    if not text:
        return jsonify({"status": "error", "error": "Texte requis"}), 400
    
    result = analyze_meal(text, method=method)
    if request.current_user and result["status"] == "success":
        uid = request.current_user["user_id"]
        add_meal(uid, {
            "text": text,
            "method": method,
            "foods": result["foods"],
            "nutrition": result["nutrition"],
        })
        result["saved"] = True
    else:
        result["saved"] = False
    return jsonify(result)

@app.route("/api/compare_ner", methods=["POST"])
def compare_ner():
    data = request.json or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"status": "error", "error": "Texte requis"}), 400

    import time
    from ner_spacy_food import extract_food_spacy
    from ner_llm_food import extract_food_llm
    from meal_analyzer import analyze_meal

    t0 = time.time()
    spacy_foods = extract_food_spacy(text)
    spacy_time = round((time.time() - t0) * 1000, 2)
    spacy_result = analyze_meal(text, method="spacy")
    spacy_result["ner_time_ms"] = spacy_time
    spacy_result["foods"] = spacy_foods

    t0 = time.time()
    llm_foods = extract_food_llm(text)
    llm_time = round((time.time() - t0) * 1000, 2)
    llm_result = analyze_meal(text, method="llm")
    llm_result["ner_time_ms"] = llm_time
    llm_result["foods"] = llm_foods

    return jsonify({"status": "success", "spacy": spacy_result, "llm": llm_result})

# ==================== HISTORIQUE ====================
@app.route("/api/history", methods=["GET"])
@token_required
def history():
    uid = request.current_user["user_id"]
    limit = request.args.get("limit", type=int)
    date_filter = request.args.get("date")
    meals = get_history(uid, limit=limit, date_filter=date_filter)
    return jsonify({"status": "success", "meals": meals, "count": len(meals)})

@app.route("/api/history/<meal_id>", methods=["DELETE"])
@token_required
def delete_meal_route(meal_id):
    uid = request.current_user["user_id"]
    if delete_meal(uid, meal_id):
        return jsonify({"status": "success", "message": "Repas supprimé"})
    return jsonify({"status": "error", "error": "Repas non trouvé"}), 404

@app.route("/api/history/clear", methods=["DELETE"])
@token_required
def clear_history_route():
    uid = request.current_user["user_id"]
    n = clear_history(uid)
    return jsonify({"status": "success", "deleted": n})

@app.route("/api/history/stats", methods=["GET"])
@token_required
def history_stats():
    uid = request.current_user["user_id"]
    days = request.args.get("days", 7, type=int)
    stats = get_stats(uid, days=days)
    return jsonify({"status": "success", "summary": stats})

# ==================== OBJECTIFS JOURNALIERS ====================
@app.route("/api/targets", methods=["GET"])
@optional_auth
def targets():
    if request.current_user:
        user_id = request.current_user["user_id"]
        try:
            if db._pg_conn:
                with db._pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT tdee, protein_goal, carbs_goal, fat_goal FROM user_profiles WHERE user_id = %s", (user_id,))
                    row = cur.fetchone()
                    if row:
                        return jsonify({"status": "success", "targets": {
                            "calories": row['tdee'],
                            "protein": row['protein_goal'],
                            "carbs": row['carbs_goal'],
                            "fat": row['fat_goal'],
                            "fiber": 25
                        }})
        except Exception as e:
            log.warning(f"Erreur chargement objectifs personnalisés: {e}")
    return jsonify({"status": "success", "targets": Config.DAILY_TARGETS})

# ==================== PROFIL UTILISATEUR ====================
def calculate_nutritional_needs(gender: str, age: int, weight_kg: float, height_cm: float, activity_level: str, goal: str = 'maintain') -> dict:
    if gender == 'male':
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    activity_factors = {
        'sedentary': 1.2, 'light': 1.375, 'moderate': 1.55,
        'active': 1.725, 'very_active': 1.9
    }
    tdee = bmr * activity_factors.get(activity_level, 1.2)

    if goal == 'lose':
        tdee -= 500
        if tdee < 1200:
            tdee = 1200
    elif goal == 'gain':
        tdee += 500

    protein_g = weight_kg * 1.8
    if goal == 'gain':
        protein_g = weight_kg * 2.2

    fat_cal = tdee * 0.25
    fat_g = fat_cal / 9
    carbs_cal = tdee - (protein_g * 4) - fat_cal
    carbs_g = carbs_cal / 4

    return {
        'tdee': round(tdee),
        'protein_g': round(protein_g, 1),
        'carbs_g': round(carbs_g, 1),
        'fat_g': round(fat_g, 1),
        'goal': goal
    }

def ensure_user_profiles_table():
    if not db._pg_conn:
        log.warning("Pas de connexion PostgreSQL, impossible de créer la table user_profiles")
        return
    try:
        with db._pg_conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id INTEGER PRIMARY KEY,
                    gender VARCHAR(10) NOT NULL,
                    age INTEGER NOT NULL,
                    weight_kg FLOAT NOT NULL,
                    height_cm FLOAT NOT NULL,
                    activity_level VARCHAR(20) NOT NULL,
                    goal VARCHAR(20) DEFAULT 'maintain',
                    tdee INTEGER DEFAULT 0,
                    protein_goal FLOAT DEFAULT 0,
                    carbs_goal FLOAT DEFAULT 0,
                    fat_goal FLOAT DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            try:
                cur.execute("ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS goal VARCHAR(20) DEFAULT 'maintain'")
            except:
                pass
            db._pg_conn.commit()
            log.info("✅ Table user_profiles vérifiée/créée")
    except Exception as e:
        log.error(f"Erreur création table user_profiles: {e}")

@app.route("/api/user/profile", methods=["GET", "POST"])
@token_required
def user_profile():
    user_id = request.current_user["user_id"]
    ensure_user_profiles_table()
    
    if request.method == "GET":
        try:
            if not db._pg_conn:
                return jsonify({"status": "error", "error": "Base de données non disponible"}), 500
            with db._pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT gender, age, weight_kg, height_cm, activity_level, goal,
                           tdee, protein_goal, carbs_goal, fat_goal
                    FROM user_profiles WHERE user_id = %s
                """, (user_id,))
                row = cur.fetchone()
                if row:
                    needs = {
                        "tdee": row["tdee"],
                        "protein_g": row["protein_goal"],
                        "carbs_g": row["carbs_goal"],
                        "fat_g": row["fat_goal"],
                        "goal": row["goal"]
                    }
                    return jsonify({"status": "success", "profile": row, "needs": needs})
                else:
                    return jsonify({"status": "success", "profile": None})
        except Exception as e:
            log.error(f"Erreur GET profile: {e}")
            return jsonify({"status": "error", "error": str(e)}), 500
    
    elif request.method == "POST":
        data = request.json or {}
        required = ["gender", "age", "weight_kg", "height_cm", "activity_level"]
        for field in required:
            if field not in data:
                return jsonify({"status": "error", "error": f"Champ manquant: {field}"}), 400
        
        gender = data["gender"]
        age = int(data["age"])
        weight_kg = float(data["weight_kg"])
        height_cm = float(data["height_cm"])
        activity_level = data["activity_level"]
        goal = data.get("goal", "maintain")
        
        needs = calculate_nutritional_needs(gender, age, weight_kg, height_cm, activity_level, goal)
        
        try:
            with db._pg_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_profiles (user_id, gender, age, weight_kg, height_cm, activity_level, goal,
                                               tdee, protein_goal, carbs_goal, fat_goal, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) DO UPDATE SET
                        gender = EXCLUDED.gender,
                        age = EXCLUDED.age,
                        weight_kg = EXCLUDED.weight_kg,
                        height_cm = EXCLUDED.height_cm,
                        activity_level = EXCLUDED.activity_level,
                        goal = EXCLUDED.goal,
                        tdee = EXCLUDED.tdee,
                        protein_goal = EXCLUDED.protein_goal,
                        carbs_goal = EXCLUDED.carbs_goal,
                        fat_goal = EXCLUDED.fat_goal,
                        updated_at = CURRENT_TIMESTAMP
                """, (user_id, gender, age, weight_kg, height_cm, activity_level, goal,
                      needs["tdee"], needs["protein_g"], needs["carbs_g"], needs["fat_g"]))
                db._pg_conn.commit()
            return jsonify({"status": "success", "needs": needs})
        except Exception as e:
            log.error(f"Erreur POST profile: {e}")
            return jsonify({"status": "error", "error": str(e)}), 500

# ==================== LANCEMENT ====================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default=5000, type=int)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    log.info(f"🚀 {Config.APP_NAME} v{Config.VERSION} → http://localhost:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)