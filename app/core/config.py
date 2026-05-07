import os
import secrets
import sys

from pydantic_settings import BaseSettings


def _default_secret_key() -> str:
    """В тестах генерируем эфемерный ключ; в проде требуем явный SECRET_KEY из env."""
    if "pytest" in sys.modules or os.getenv("TESTING"):
        return secrets.token_urlsafe(32)
    raise RuntimeError(
        "SECRET_KEY не задан. Установите переменную окружения SECRET_KEY "
        "(например, через .env). Сгенерировать можно через `openssl rand -hex 32`."
    )


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./rental.db"
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

    def model_post_init(self, __context) -> None:
        if not self.SECRET_KEY:
            self.SECRET_KEY = _default_secret_key()


settings = Settings()
