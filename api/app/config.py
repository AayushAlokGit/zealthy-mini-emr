"""Application settings, loaded from environment with sensible dev defaults."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./zealthy.db"

    # Logging verbosity (DEBUG | INFO | WARNING | ERROR).
    log_level: str = "INFO"

    # Seed the DB from data.json on startup when it has no patients yet.
    # Convenient for ephemeral demo hosts that reset the SQLite file on deploy.
    seed_on_startup: bool = True

    # Auth
    jwt_secret: str = "dev-secret-change-in-production-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 1 day
    cookie_name: str = "zealthy_session"
    cookie_secure: bool = False  # set True behind HTTPS in production
    # "lax" for local dev (same-site localhost); "none" for cross-site prod
    # (Vercel frontend + separate API domain) — which also requires secure=True.
    cookie_samesite: str = "lax"

    # CORS — the deployed frontend origin(s)
    frontend_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


settings = Settings()
