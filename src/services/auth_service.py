from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.config.settings import Settings


@dataclass(frozen=True)
class AuthResult:
    ok: bool
    username: Optional[str] = None
    role: Optional[str] = None
    error: Optional[str] = None


def _hash_password(password: str, salt: str) -> str:
    # Suficiente para demo interna. En prod usarías bcrypt/argon2 o SSO.
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


class AuthService:
    def authenticate(self, username: str, password: str) -> AuthResult:
        raise NotImplementedError


class FileAuthService(AuthService):
    def __init__(self, users_path: Path, salt: str):
        self.users_path = users_path
        self.salt = salt

    def authenticate(self, username: str, password: str) -> AuthResult:
        username = (username or "").strip()
        password = password or ""

        if not username or not password:
            return AuthResult(ok=False, error="Usuario y contraseña son requeridos.")

        if not self.users_path.exists():
            return AuthResult(ok=False, error=f"No existe el archivo de usuarios: {self.users_path}")

        try:
            raw = self.users_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except Exception as ex:
            return AuthResult(ok=False, error=f"No se pudo leer users.json: {ex}")

        users = data.get("users", [])
        user = next((u for u in users if (u.get("username") or "").strip().lower() == username.lower()), None)
        if not user:
            return AuthResult(ok=False, error="Usuario o contraseña incorrectos.")

        expected_hash = user.get("password_hash") or ""
        given_hash = _hash_password(password, self.salt)

        if given_hash != expected_hash:
            return AuthResult(ok=False, error="Usuario o contraseña incorrectos.")

        return AuthResult(ok=True, username=user.get("username"), role=user.get("role"))


class ApiAuthService(AuthService):
    """
    Placeholder (futuro): aquí harías POST /login y recibirías token.
    """
    def __init__(self, base_url: str):
        self.base_url = base_url

    def authenticate(self, username: str, password: str) -> AuthResult:
        return AuthResult(ok=False, error="AUTH_MODE=api aún no está implementado.")


def build_auth_service(settings: Settings) -> AuthService:
    if settings.AUTH_MODE == "file":
        return FileAuthService(settings.USERS_PATH, settings.AUTH_SALT)
    if settings.AUTH_MODE == "api":
        return ApiAuthService(settings.API_BASE_URL)
    return FileAuthService(settings.USERS_PATH, settings.AUTH_SALT)
