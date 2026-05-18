import os

class Settings:
    @property
    def supabase_url(self) -> str:
        return os.environ["SUPABASE_URL"]

    @property
    def supabase_anon_key(self) -> str:
        return os.environ["SUPABASE_ANON_KEY"]

    @property
    def supabase_service_key(self) -> str:
        return os.environ["SUPABASE_SERVICE_KEY"]

settings = Settings()