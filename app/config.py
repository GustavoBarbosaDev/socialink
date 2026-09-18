from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Configurações gerais
    APP_NAME: str = "Socialink"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Banco de dados
    DATABASE_URL: str = "sqlite:///./socialink.db"

    # JWT
    SECRET_KEY: str = "sua_chave_secreta_aqui_mude_em_producao"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
