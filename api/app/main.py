from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import courses, sections, analytics, department

app = FastAPI(
    title="PantherGrades API",
    description="GSU grade distribution data for students.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://panther-grades.vercel.app",
        "https://panthergrades.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(courses.router)
app.include_router(sections.router)
app.include_router(analytics.router)
app.include_router(department.router)


@app.get("/health")
def health():
    return {"status": "ok"}