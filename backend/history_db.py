import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config

log = logging.getLogger("NutriVoice.History")

class HistoryDB:
    def __init__(self):
        self.conn = None
        self._connect()

    def _connect(self):
        try:
            self.conn = psycopg2.connect(
                host=Config.DB_HOST, port=Config.DB_PORT,
                dbname=Config.DB_NAME, user=Config.DB_USER,
                password=Config.DB_PASSWORD
            )
            self.conn.autocommit = True
            self._ensure_tables()
            log.info("✅ Historique connecté à PostgreSQL")
        except Exception as e:
            log.error(f"Erreur de connexion historique: {e}")
            self.conn = None

    def _ensure_tables(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_meals (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    meal_text TEXT NOT NULL,
                    foods JSONB NOT NULL,
                    nutrition JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_user_meals_user_id ON user_meals(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_user_meals_created_at ON user_meals(created_at)")

    def add_meal(self, user_id: int, meal_text: str, foods: List[Dict], nutrition: Dict) -> Dict:
        if not self.conn:
            log.warning("Pas de connexion PostgreSQL, repas non sauvegardé")
            return {}
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO user_meals (user_id, meal_text, foods, nutrition)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, user_id, meal_text, foods, nutrition, created_at
                """, (user_id, meal_text, json.dumps(foods), json.dumps(nutrition)))
                row = cur.fetchone()
                return dict(row)
        except Exception as e:
            log.error(f"Erreur add_meal: {e}")
            return {}

    def get_history(self, user_id: int, limit: Optional[int] = None,
                    start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        if not self.conn:
            return []
        try:
            query = """
                SELECT id, meal_text, foods, nutrition, created_at
                FROM user_meals
                WHERE user_id = %s
            """
            params = [user_id]
            if start_date:
                query += " AND created_at >= %s"
                params.append(start_date)
            if end_date:
                query += " AND created_at <= %s"
                params.append(end_date)
            query += " ORDER BY created_at DESC"
            if limit:
                query += " LIMIT %s"
                params.append(limit)
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                return rows
        except Exception as e:
            log.error(f"Erreur get_history: {e}")
            return []

    def delete_meal(self, user_id: int, meal_id: int) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM user_meals WHERE id = %s AND user_id = %s", (meal_id, user_id))
                return cur.rowcount > 0
        except Exception as e:
            log.error(f"Erreur delete_meal: {e}")
            return False

    def clear_history(self, user_id: int) -> int:
        if not self.conn:
            return 0
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM user_meals WHERE user_id = %s", (user_id,))
                return cur.rowcount
        except Exception as e:
            log.error(f"Erreur clear_history: {e}")
            return 0

    def get_stats(self, user_id: int, days: int = 7) -> Dict:
        cutoff = datetime.now() - timedelta(days=days)
        meals = self.get_history(user_id, start_date=cutoff.isoformat())
        if not meals:
            return {
                "total_meals": 0,
                "days_tracked": 0,
                "daily_averages": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0},
                "weekly_trend": [],
                "top_foods": [],
                "macro_distribution": {"protein": 0, "carbs": 0, "fat": 0},
            }
        by_date = {}
        food_counts = {}
        for meal in meals:
            date_key = meal['created_at'].strftime("%Y-%m-%d")
            if date_key not in by_date:
                by_date[date_key] = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
            nut = meal['nutrition']
            for k in ("calories", "protein", "carbs", "fat"):
                by_date[date_key][k] += nut.get(k, 0)
            for food in meal['foods']:
                name = food.get('food_ar') or food.get('food', '')
                if name:
                    food_counts[name] = food_counts.get(name, 0) + 1

        totals = {k: sum(d[k] for d in by_date.values()) for k in ("calories", "protein", "carbs", "fat")}
        n_days = len(by_date) or 1
        daily_averages = {k: round(totals[k] / n_days, 1) for k in totals}
        macro_sum = daily_averages["protein"] + daily_averages["carbs"] + daily_averages["fat"] or 1
        macro_distribution = {
            "protein": round(daily_averages["protein"] / macro_sum * 100, 1),
            "carbs":   round(daily_averages["carbs"]   / macro_sum * 100, 1),
            "fat":     round(daily_averages["fat"]      / macro_sum * 100, 1),
        }
        today = datetime.now().date()
        weekly_trend = []
        for i in range(6, -1, -1):
            d = (today - timedelta(days=i)).isoformat()
            weekly_trend.append({
                "date": d,
                "day": ["Dim", "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam"][(today - timedelta(days=i)).weekday() % 7],
                "calories": round(by_date.get(d, {}).get("calories", 0), 1),
            })
        top_foods = sorted(food_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        return {
            "total_meals": len(meals),
            "days_tracked": n_days,
            "daily_averages": daily_averages,
            "weekly_trend": weekly_trend,
            "top_foods": [{"name": k, "count": v} for k, v in top_foods],
            "macro_distribution": macro_distribution,
        }

_history_db = None

def get_history_db():
    global _history_db
    if _history_db is None:
        _history_db = HistoryDB()
    return _history_db

def add_meal(user_id: int, meal: dict):
    db = get_history_db()
    return db.add_meal(
        user_id,
        meal.get("text", ""),
        meal.get("foods", []),
        meal.get("nutrition", {})
    )

def get_history(user_id: int, limit: int = None, date_filter: str = None):
    db = get_history_db()
    return db.get_history(user_id, limit=limit, start_date=date_filter)

def delete_meal(user_id: int, meal_id: str):
    return get_history_db().delete_meal(user_id, int(meal_id))

def clear_history(user_id: int):
    return get_history_db().clear_history(user_id)

def get_stats(user_id: int, days: int = 7):
    return get_history_db().get_stats(user_id, days)