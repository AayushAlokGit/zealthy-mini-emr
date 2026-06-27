from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./zealthy.db"

    log_level: str = "INFO"  # DEBUG | INFO | WARNING | ERROR

    seed_on_startup: bool = True

    jwt_secret: str = "dev-secret-change-in-production-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 1 day
    cookie_name: str = "zealthy_session"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"  # "lax" | "none" (none requires secure=True)

    frontend_origins: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


settings = Settings()
