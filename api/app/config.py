from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,   # match SUPABASE_URL → supabase_url
        extra="ignore",         # ignore Railway's own injected variables
    )


settings = Settings()