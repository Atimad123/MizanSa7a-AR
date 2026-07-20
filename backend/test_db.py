from postgres_client import db
print("دجاج 100g:", db.get_nutrition_by_arabic_name('دجاج', 100))
print("بيض 165g:", db.get_nutrition_by_arabic_name('بيض', 165))