@app.get("/debug-env")
def debug_env():
    import os
    url = os.environ.get("SUPABASE_URL", "NOT SET")
    anon = os.environ.get("SUPABASE_ANON_KEY", "NOT SET")
    service = os.environ.get("SUPABASE_SERVICE_KEY", "NOT SET")
    return {
        "SUPABASE_URL": url,
        "SUPABASE_ANON_KEY_length": len(anon),
        "SUPABASE_ANON_KEY_first10": anon[:10],
        "SUPABASE_SERVICE_KEY_length": len(service),
    }