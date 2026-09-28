from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Placeholders que o .env.example traz. Aceitá-los em produção permitiria
# assinar JWT com uma chave conhecida por qualquer pessoa que leia o repo.
PLACEHOLDERS_DE_SECRET_KEY = frozenset(
    {
        "sua_chave_secreta_aqui",
        "sua_chave_secreta_aqui_mude_em_producao",
    }
)

MENSAGEM_SECRET_KEY = (
    "SECRET_KEY ausente ou ainda é um placeholder do .env.example. "
    "Copie .env.example para .env e gere uma chave real: openssl rand -hex 32"
)


class Settings(BaseSettings):
    # Configurações gerais
    APP_NAME: str = "Socialink"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Banco de dados
    DATABASE_URL: str = "sqlite:///./socialink.db"

    # JWT
    SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @model_validator(mode="after")
    def secret_key_e_segura(self):
        if (
            not self.SECRET_KEY.strip()
            or self.SECRET_KEY in PLACEHOLDERS_DE_SECRET_KEY
        ):
            raise ValueError(MENSAGEM_SECRET_KEY)
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
