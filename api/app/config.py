import os

class Settings:
    supabase_url: str = os.environ["SUPABASE_URL"]
    supabase_anon_key: str = os.environ["SUPABASE_ANON_KEY"]
    supabase_service_key: str = os.environ["SUPABASE_SERVICE_KEY"]

settings = Settings()