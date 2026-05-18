from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import courses, sections, analytics

app = FastAPI(
    title="PantherGrades API",
    description="GSU grade distribution data for students.",
    version="0.1.0",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
# Tighten origins before going to production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # add your Vercel URL here later
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(courses.router)
app.include_router(sections.router)
app.include_router(analytics.router)


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/debug-env")
def debug_env():
    import os
    return {
        "SUPABASE_URL": os.environ.get("SUPABASE_URL", "NOT SET"),
        "SUPABASE_ANON_KEY": os.environ.get("SUPABASE_ANON_KEY", "NOT SET")[:10] + "...",
        "SUPABASE_SERVICE_KEY": os.environ.get("SUPABASE_SERVICE_KEY", "NOT SET")[:10] + "...",
    }