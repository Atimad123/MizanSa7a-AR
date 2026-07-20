import hashlib, secrets, json
import re
from pathlib import Path
from datetime import datetime
import logging
from config import Config

log = logging.getLogger("NutriVoice.UserManager")
USER_FILE = Config.USER_FILE

def _hash_password(pwd: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pwd.encode(), salt.encode(), 200_000)
    return f"{salt}:{h.hex()}"

def _verify_password(pwd: str, hashed: str) -> bool:
    try:
        salt, stored = hashed.split(":", 1)
        h = hashlib.pbkdf2_hmac("sha256", pwd.encode(), salt.encode(), 200_000)
        return h.hex() == stored
    except Exception:
        return False

def _validate_email(email: str) -> bool:
    return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", email))

def _validate_password(pwd: str) -> str:
    if len(pwd) < 6:
        return "Le mot de passe doit contenir au moins 6 caractères"
    return None

class UserManager:
    def __init__(self):
        self._load()

    def _load(self):
        if USER_FILE.exists():
            try:
                with open(USER_FILE, "r", encoding="utf-8") as f:
                    self.users = json.load(f)
            except Exception:
                self.users = []
        else:
            self.users = []

    def _save(self):
        with open(USER_FILE, "w", encoding="utf-8") as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)

    def register(self, username: str, email: str, password: str) -> dict:
        username = username.strip()
        email = email.strip().lower()
        if not username or len(username) < 2:
            return {"status": "error", "error": "Nom d'utilisateur invalide (min 2)"}
        if not _validate_email(email):
            return {"status": "error", "error": "Email invalide"}
        pwd_err = _validate_password(password)
        if pwd_err:
            return {"status": "error", "error": pwd_err}
        self._load()
        for u in self.users:
            if u["email"] == email:
                return {"status": "error", "error": "Email déjà utilisé"}
            if u["username"].lower() == username.lower():
                return {"status": "error", "error": "Nom d'utilisateur déjà pris"}
        new_id = max((u["id"] for u in self.users), default=0) + 1
        new_user = {
            "id": new_id,
            "username": username,
            "email": email,
            "password_hash": _hash_password(password),
            "created_at": datetime.now().isoformat(),
            "last_login": None,
        }
        self.users.append(new_user)
        self._save()
        log.info(f"Nouvel utilisateur: {username} ({email})")
        return {"status": "success", "user": {"id": new_id, "username": username, "email": email}}

    def login(self, email: str, password: str) -> dict:
        email = email.strip().lower()
        self._load()
        for u in self.users:
            if u["email"] == email:
                if _verify_password(password, u["password_hash"]):
                    u["last_login"] = datetime.now().isoformat()
                    self._save()
                    return {"status": "success", "user": {"id": u["id"], "username": u["username"], "email": u["email"]}}
                return {"status": "error", "error": "Mot de passe incorrect"}
        return {"status": "error", "error": "Email non trouvé"}

    def get_by_id(self, user_id: int):
        self._load()
        for u in self.users:
            if u["id"] == user_id:
                return {"id": u["id"], "username": u["username"], "email": u["email"]}
        return None

    def change_password(self, user_id: int, old_pwd: str, new_pwd: str) -> dict:
        self._load()
        for u in self.users:
            if u["id"] == user_id:
                if not _verify_password(old_pwd, u["password_hash"]):
                    return {"status": "error", "error": "Ancien mot de passe incorrect"}
                err = _validate_password(new_pwd)
                if err:
                    return {"status": "error", "error": err}
                u["password_hash"] = _hash_password(new_pwd)
                self._save()
                return {"status": "success"}
        return {"status": "error", "error": "Utilisateur non trouvé"}

user_manager = UserManager()