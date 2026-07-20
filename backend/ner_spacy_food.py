import logging
from typing import List, Dict

log = logging.getLogger("NutriVoice.NER.spaCy")

_nlp = None
_spacy_available = False

def get_nlp():
    global _nlp, _spacy_available
    if _spacy_available:
        return _nlp
    try:
        import spacy
        from config import Config
        try:
            _nlp = spacy.load(Config.SPACY_MODEL)
            _spacy_available = True
            log.info("✅ spaCy model loaded")
        except OSError:
            log.warning(f"spaCy model '{Config.SPACY_MODEL}' not found. Using fallback.")
            _spacy_available = False
    except ImportError:
        log.warning("spaCy not installed. Using fallback.")
        _spacy_available = False
    return _nlp

def get_known_foods():
    try:
        from meal_analyzer import ALL_FOODS
        return ALL_FOODS
    except ImportError:
        return {
            "دجاج", "بيض", "رز", "خبز", "حليب", "تفاح", "موز", "سمك",
            "لحم بقر", "لحم غنم", "زبادي", "جبن", "زيت زيتون", "تمر", "عسل",
            "كسكس", "بطاطا", "طماطم", "خيار", "جزر", "طاجين", "مسمن"
        }

UNITS = {
    "غرام": "g", "غ": "g", "جرام": "g",
    "كيلو": "kg", "كغ": "kg", "كيلوغرام": "kg",
    "ملعقة صغيرة": "tsp", "ملعقة شاي": "tsp",
    "ملعقة كبيرة": "tbsp", "ملعقة أكل": "tbsp",
    "كأس": "cup", "كوب": "cup", "قدح": "cup",
    "حبة": "piece", "قطعة": "piece"
}
def extract_food_spacy(text: str):
    from meal_analyzer import extract_foods_from_text
    return extract_foods_from_text(text)

    

def _fallback_extraction(text: str) -> List[Dict]:
    known = get_known_foods()
    foods = []
    for word in known:
        if word in text:
            foods.append({
                "food_ar": word,
                "food_en": word,
                "quantity": 100,
                "unit": "g",
                "weight_g": 100
            })
    return foods