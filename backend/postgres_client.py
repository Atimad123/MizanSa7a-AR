import logging
import re
import unicodedata
from typing import Optional, Dict
import psycopg2
from config import Config

log = logging.getLogger("NutriVoice.DB")

def normalize_arabic(text: str) -> str:
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'[أإآ]', 'ا', text)
    text = re.sub(r'ة\b', 'ه', text)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    text = text.replace('قبليه', 'فيليه')
    text = text.replace('فيلي', 'فيليه')
    return text.strip()

# Table de correspondance des variantes → nom canonique
FOOD_NORMALIZATION = {
    "بيض": "بيض", "بيضة": "بيض", "بيضات": "بيض", "بيضه": "بيض",
    "يبض": "بيض", "يبضات": "بيض", "بضع": "بيض", "بض": "بيض",
    "دجاج": "دجاج",
    "رز": "رز", "أرز": "رز",
    "خبز": "خبز",
    "حليب": "حليب",
    "موز": "موز", "موزة": "موز",
    "تفاح": "تفاح", "تفاحة": "تفاح",
    "تمر": "تمر", "تمرة": "تمر",
    "عسل": "عسل",
    "كسكس": "كسكس",
    "مسمن": "مسمن",
    "شاي": "شاي",
    "زبادي": "زبادي",
    "جبن": "جبن",
    "زيت زيتون": "زيت زيتون",
    "بطاطا": "بطاطا",
    "طماطم": "طماطم",
    "خيار": "خيار",
    "جزر": "جزر",
}

class PostgresClient:
    def __init__(self):
        self._pg_conn = None
        self._try_postgres()

    def _try_postgres(self):
        try:
            self._pg_conn = psycopg2.connect(
                host=Config.DB_HOST, port=Config.DB_PORT,
                dbname=Config.DB_NAME, user=Config.DB_USER,
                password=Config.DB_PASSWORD, connect_timeout=3
            )
            log.info("✅ PostgreSQL connecté")
        except Exception as e:
            log.error(f"PostgreSQL indisponible: {e}")
            self._pg_conn = None

    def get_nutrition_by_arabic_name(self, food_name: str, weight_g: float = 100) -> Optional[Dict]:
        if not self._pg_conn:
            return None

        # 1. Normaliser le nom (supprimer diacritiques, variantes)
        normalized_input = normalize_arabic(food_name)
        # 2. Appliquer la table de correspondance
        canonical_name = FOOD_NORMALIZATION.get(normalized_input, normalized_input)

        try:
            with self._pg_conn.cursor() as cur:
                # Recherche exacte du nom canonique
                cur.execute("""
                    SELECT name_ar, calories, proteines, glucides, lipides
                    FROM nutrition
                    WHERE name_ar = %s
                    LIMIT 1
                """, (canonical_name,))
                row = cur.fetchone()
                # Si pas trouvé, recherche floue (au cas où)
                if not row:
                    cur.execute("""
                        SELECT name_ar, calories, proteines, glucides, lipides
                        FROM nutrition
                        WHERE name_ar ILIKE %s
                        ORDER BY LENGTH(name_ar) ASC
                        LIMIT 1
                    """, (f"%{canonical_name}%",))
                    row = cur.fetchone()
                if row:
                    factor = weight_g / 100.0
                    return {
                        "name_ar": row[0],
                        "source": "postgres",
                        "weight_g": weight_g,
                        "calories": round(row[1] * factor, 1),
                        "protein":  round(row[2] * factor, 1),
                        "carbs":    round(row[3] * factor, 1),
                        "fat":      round(row[4] * factor, 1),
                        "fiber":    0.0,
                    }
        except Exception as e:
            log.warning(f"Query error: {e}")
        return None

    def status(self) -> dict:
        return {
            "connected": self._pg_conn is not None,
            "backend": "postgresql" if self._pg_conn else "none",
            "local_foods": 0,
        }

db = PostgresClient()