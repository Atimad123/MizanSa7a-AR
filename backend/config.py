import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "nutrivoice-secret-key-change-in-production-2024!")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "nutrivoice-jwt-key-change-in-production-2024!")
    JWT_EXPIRY_DAYS = int(os.getenv("JWT_EXPIRY_DAYS", 7))

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 5432))
    DB_NAME = os.getenv("DB_NAME", "nutrivoice_db")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    APP_NAME = "NutriVoice-AR"
    VERSION = "3.2.0"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    DAILY_TARGETS = {
        "calories": 2000,
        "protein": 50,
        "carbs": 250,
        "fat": 70,
        "fiber": 25,
    }

    USER_FILE = Path(os.getenv("USER_FILE", "users_fallback.json"))
    HISTORY_FILE = Path(os.getenv("HISTORY_FILE", "meal_history.json"))

    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
    SPACY_MODEL = os.getenv("SPACY_MODEL", "ar_core_web_sm")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    USE_REAL_LLM = os.getenv("USE_REAL_LLM", "false").lower() == "true"
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")