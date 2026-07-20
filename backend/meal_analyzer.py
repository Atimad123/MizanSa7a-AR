import re
import time
from typing import List, Dict
from postgres_client import db, normalize_arabic
from ner_spacy_food import extract_food_spacy
from ner_llm_food import extract_food_llm

# ==================== DICTIONNAIRES ====================

NUMBERS = {
    "نصف": 0.5, "ربع": 0.25, "ثلث": 0.33,
    "واحد": 1, "واحدة": 1, "اثنين": 2, "اثنتين": 2,
    "ثلاث": 3, "ثلاثة": 3, "اربع": 4, "اربعة": 4,
    "خمس": 5, "خمسة": 5, "ست": 6, "ستة": 6,
    "سبع": 7, "سبعة": 7, "ثمان": 8, "ثمانية": 8,
    "تسع": 9, "تسعة": 9, "عشر": 10, "عشرة": 10,
}

UNIT_CONVERSION = {
    "غرام": 1.0, "غ": 1.0, "جرام": 1.0,
    "كيلو": 1000.0, "كغ": 1000.0,
    "مل": 1.0, "ملليلتر": 1.0, "لتر": 1000.0,
    "ملعقة صغيرة": 5.0, "ملعقة شاي": 5.0,
    "ملعقة كبيرة": 15.0, "ملعقة أكل": 15.0,
    "كأس": 250.0, "كوب": 250.0, "قدح": 200.0,
    "حبة": None, "قطعة": None,
}

PIECE_WEIGHTS = {
    "بيض": 55, "بيضة": 55, "بيضات": 55,
    "موز": 120, "موزة": 120,
    "تفاح": 150, "تفاحة": 150,
    "خبز": 50, "رغيف": 50,
    "جبن": 30,
    "تمر": 8, "تمرة": 8,
    "طماطم": 100, "طماطمة": 100,
    "خيار": 120, "خيارة": 120,
    "جزر": 80, "جزرة": 80,
    "بطاطا": 150,
    "مسمن": 150,
    "شاورما": 200,
}

COMPOSITE_FOODS = [
    "فيليه دجاج مشوي",
    "طاجين الدجاج", "طاجين اللحم", "طاجين السمك", "طاجين الخضار",
    "الكسكس بالدجاج", "الكسكس باللحم", "الكسكس بالخضار", "الكسكس بالسمك",
    "شاورما الدجاج", "شاورما اللحم", "شاورما السمك",
]

AR_TO_EN = {
    "دجاج": "chicken", "بيض": "egg", "بيضة": "egg", "بيضات": "egg",
    "رز": "rice", "خبز": "bread", "حليب": "milk", "تفاح": "apple", "موز": "banana",
    "سمك": "fish", "لحم بقر": "beef", "لحم غنم": "lamb", "زبادي": "yogurt",
    "جبن": "cheese", "زيت زيتون": "olive oil", "تمر": "dates", "عسل": "honey",
    "كسكس": "couscous", "بطاطا": "potato", "طماطم": "tomato", "خيار": "cucumber",
    "جزر": "carrot", "مسمن": "msemen", "فيليه دجاج مشوي": "grilled chicken fillet",
    "طاجين الدجاج": "chicken tagine", "الكسكس بالدجاج": "couscous with chicken",
    "شاورما الدجاج": "chicken shawarma",
}

ALL_FOODS = sorted(set(AR_TO_EN.keys()) | set(COMPOSITE_FOODS), key=len, reverse=True)

def canonical_food(name: str) -> str:
    """Retourne le nom canonique (ex: بيضات -> بيض, بيضة -> بيض)."""
    name = name.replace('ات', '')
    name = name.replace('ة', '')
    return name

def convert_to_grams(food_ar: str, quantity: float, unit: str) -> float:
    unit = unit.strip().lower()
    if unit in ("g", "غرام", "غ", "جرام"):
        return quantity
    if unit in ("kg", "كغ", "كيلو", "كيلوغرام"):
        return quantity * 1000
    if unit in ("piece", "حبة", "قطعة"):
        weight_per_piece = PIECE_WEIGHTS.get(food_ar, 50)
        return quantity * weight_per_piece
    if unit in ("ملعقة صغيرة", "ملعقة شاي", "tsp"):
        return quantity * 5
    if unit in ("ملعقة كبيرة", "ملعقة أكل", "tbsp"):
        return quantity * 15
    if unit in ("كأس", "كوب", "قدح", "cup"):
        return quantity * 250
    if unit in ("مل", "ملليلتر", "ml"):
        return quantity
    if unit in ("لتر", "ل", "l"):
        return quantity * 1000
    return quantity

def normalize_text(text: str) -> str:
    text = re.sub(r'[أإآ]', 'ا', text)
    text = re.sub(r'ة\b', 'ه', text)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    return text.strip()

def parse_quantity(q: str) -> float:
    if q in NUMBERS:
        return NUMBERS[q]
    try:
        return float(q.replace(',', '.'))
    except:
        return 1.0

def detect_unit(unit_text: str):
    unit_text = unit_text.strip()
    for u, factor in sorted(UNIT_CONVERSION.items(), key=len, reverse=True):
        if u in unit_text:
            return u, factor
    return "g", 1.0

def build_patterns():
    num_pat = r'\d+(?:[.,]\d+)?|' + '|'.join(re.escape(n) for n in NUMBERS)
    unit_pat = '|'.join(re.escape(u) for u in UNIT_CONVERSION)
    food_pat = '|'.join(re.escape(f) for f in ALL_FOODS)
    return num_pat, unit_pat, food_pat

NUM_PAT, UNIT_PAT, FOOD_PAT = build_patterns()

def extract_foods_from_text(text: str) -> List[Dict]:
    text = normalize_arabic(text)
    norm = normalize_text(text)
    
    # Dictionnaire temporaire pour accumuler les poids par nom canonique
    temp_foods = {}  # canonical_name -> {'food_ar': original, 'weight_g': total, 'unit_display': ...}
    
    # Pattern A: quantité + unité + aliment
    pat_a = re.compile(rf'({NUM_PAT})\s*({UNIT_PAT})\s+(.{{1,30}})', re.UNICODE)
    for m in pat_a.finditer(norm):
        qty = parse_quantity(m.group(1))
        unit_text, _ = detect_unit(m.group(2))
        rest = m.group(3).strip()
        for food in ALL_FOODS:
            if food in rest:
                weight = convert_to_grams(food, qty, unit_text)
                canon = canonical_food(food)
                if canon not in temp_foods:
                    temp_foods[canon] = {
                        "food_ar": food,
                        "weight_g": weight,
                        "unit": m.group(2),
                        "original_name": food
                    }
                else:
                    temp_foods[canon]["weight_g"] += weight
                break
    
    # Pattern B: nombre + aliment (unité implicite = pièce)
    pat_b = re.compile(rf'({NUM_PAT})\s+({FOOD_PAT})', re.UNICODE)
    for m in pat_b.finditer(norm):
        qty = parse_quantity(m.group(1))
        food = m.group(2)
        weight = convert_to_grams(food, qty, "piece")
        canon = canonical_food(food)
        if canon not in temp_foods:
            temp_foods[canon] = {
                "food_ar": food,
                "weight_g": weight,
                "unit": "حبة",
                "original_name": food
            }
        else:
            temp_foods[canon]["weight_g"] += weight
    
    # Pattern D: aliment + nombre (ex: بيضة واحدة)
    pat_d = re.compile(rf'({FOOD_PAT})\s+({NUM_PAT})', re.UNICODE)
    for m in pat_d.finditer(norm):
        food = m.group(1)
        qty = parse_quantity(m.group(2))
        weight = convert_to_grams(food, qty, "piece")
        canon = canonical_food(food)
        if canon not in temp_foods:
            temp_foods[canon] = {
                "food_ar": food,
                "weight_g": weight,
                "unit": "حبة",
                "original_name": food
            }
        else:
            temp_foods[canon]["weight_g"] += weight
    
    # Pattern C: aliment seul (100g par défaut) – seulement si jamais vu
    for food in ALL_FOODS:
        if food in norm:
            canon = canonical_food(food)
            if canon not in temp_foods:
                weight = 100.0
                temp_foods[canon] = {
                    "food_ar": food,
                    "weight_g": weight,
                    "unit": "g",
                    "original_name": food
                }
    
    # Convertir le dictionnaire en liste finale
    foods = []
    for canon, data in temp_foods.items():
        foods.append({
            "food_ar": data["original_name"],
            "food_en": AR_TO_EN.get(canon, canon),
            "quantity": round(data["weight_g"] / (PIECE_WEIGHTS.get(canon, 50) if data["unit"] == "حبة" else 1), 2),
            "unit": data["unit"],
            "weight_g": round(data["weight_g"], 1)
        })
    return foods

def analyze_meal(text: str, method: str = "normalizer") -> Dict:
    t0 = time.time()
    if method == "spacy":
        foods = extract_food_spacy(text)
    elif method == "llm":
        foods = extract_food_llm(text)
    else:
        foods = extract_foods_from_text(text)

    total = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0, "fiber": 0.0}
    enriched = []

    for f in foods:
        nut = db.get_nutrition_by_arabic_name(f["food_ar"], f["weight_g"])
        if nut:
            for k in total:
                total[k] += nut.get(k, 0)
            f["nutrition"] = nut
            f["found"] = True
        else:
            f["found"] = False
            f["nutrition"] = None

        if "food_en" not in f or f["food_en"] == f["food_ar"]:
            f["food_en"] = AR_TO_EN.get(f["food_ar"], f["food_ar"])
        enriched.append(f)

    return {
        "status": "success",
        "foods": enriched,
        "nutrition": {k: round(v, 1) for k, v in total.items()},
        "foods_found": sum(1 for f in enriched if f["found"]),
        "foods_total": len(enriched),
        "ner_time_ms": round((time.time() - t0) * 1000, 1),
        "db_source": db.status()["backend"],
        "method_used": method,
    }