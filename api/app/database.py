from supabase import create_client, Client
from app.config import settings

# Public client — respects RLS, safe for user-facing queries
def get_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_anon_key)

# Service client — bypasses RLS, for admin/webhook use only
def get_service_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_key)