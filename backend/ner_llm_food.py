import json
import logging
import os
from typing import List, Dict

log = logging.getLogger("NutriVoice.NER.LLM")

from config import Config

OPENAI_API_KEY = getattr(Config, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = getattr(Config, "ANTHROPIC_API_KEY", None) or os.getenv("ANTHROPIC_API_KEY")
USE_REAL_LLM = getattr(Config, "USE_REAL_LLM", False)

OPENAI_AVAILABLE = False
ANTHROPIC_AVAILABLE = False

if OPENAI_API_KEY:
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
        OPENAI_AVAILABLE = True
    except ImportError:
        pass
if ANTHROPIC_API_KEY:
    try:
        import anthropic
        ANTHROPIC_AVAILABLE = True
    except ImportError:
        pass

def extract_food_llm(text: str) -> List[Dict]:
    if USE_REAL_LLM and OPENAI_AVAILABLE:
        try:
            response = openai.ChatCompletion.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Extrais les aliments en arabe avec leur quantité approximative. Réponds uniquement au format JSON : [{\"food_ar\": \"nom\", \"quantity\": nombre, \"unit\": \"g\"}]"},
                    {"role": "user", "content": text}
                ],
                temperature=0
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            foods = []
            for item in data:
                weight = item.get("quantity", 100)
                foods.append({
                    "food_ar": item["food_ar"],
                    "food_en": item["food_ar"],
                    "quantity": weight,
                    "unit": item.get("unit", "g"),
                    "weight_g": float(weight)
                })
            return foods
        except Exception as e:
            log.warning(f"LLM extraction failed: {e}")
            return _fallback_extraction(text)
    else:
        return _fallback_extraction(text)

def _fallback_extraction(text: str) -> List[Dict]:
    try:
        from meal_analyzer import extract_foods_from_text
        return extract_foods_from_text(text)
    except ImportError:
        from meal_analyzer import ALL_FOODS
        foods = []
        for word in ALL_FOODS:
            if word in text:
                foods.append({
                    "food_ar": word,
                    "food_en": word,
                    "quantity": 100,
                    "unit": "g",
                    "weight_g": 100
                })
        return foods