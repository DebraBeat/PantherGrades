"""
/courses routes
---------------
GET /courses                  — paginated list with optional filters
GET /courses/search?q=        — search by course code or title
GET /courses/departments       — list all unique departments
GET /courses/{course_code}    — single course detail with section summary
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.database import get_client

router = APIRouter(prefix="/courses", tags=["courses"])


# ── Response models ────────────────────────────────────────────────────────────

class Course(BaseModel):
    id: str
    course_code: str
    department: Optional[str]
    course_number: Optional[str]
    title: Optional[str]


class CourseDetail(BaseModel):
    id: str
    course_code: str
    department: Optional[str]
    course_number: Optional[str]
    title: Optional[str]
    total_sections: int
    avg_gpa: Optional[float]
    avg_dwf_pct: Optional[float]


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[Course])
def list_courses(
    department: Optional[str] = Query(None, description="Filter by department code e.g. ACCT"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Return a paginated list of courses, optionally filtered by department."""
    client = get_client()
    query = client.table("courses").select("id, course_code, department, course_number, title")

    if department:
        query = query.eq("department", department.upper())

    result = query.order("course_code").range(offset, offset + limit - 1).execute()
    return result.data


@router.get("/search", response_model=list[Course])
def search_courses(
    q: str = Query(..., min_length=2, description="Search term — course code or department"),
    limit: int = Query(20, ge=1, le=50),
):
    """
    Search courses by course code prefix.
    e.g. /courses/search?q=ACCT returns all accounting courses.
    e.g. /courses/search?q=2102 matches course numbers containing 2102.
    """
    client = get_client()

    # Try matching course_code prefix first (most common use case)
    result = (
        client.table("courses")
        .select("id, course_code, department, course_number, title")
        .ilike("course_code", f"{q.upper()}%")
        .order("course_code")
        .limit(limit)
        .execute()
    )

    # If no prefix match, fall back to contains search
    if not result.data:
        result = (
            client.table("courses")
            .select("id, course_code, department, course_number, title")
            .ilike("course_code", f"%{q.upper()}%")
            .order("course_code")
            .limit(limit)
            .execute()
        )

    return result.data


@router.get("/departments", response_model=list[str])
def list_departments():
    """Return all unique department codes, sorted alphabetically."""
    client = get_client()
    result = (
        client.table("courses")
        .select("department")
        .order("department")
        .execute()
    )
    # Deduplicate and strip None values
    seen = set()
    departments = []
    for row in result.data:
        d = row.get("department")
        if d and d not in seen:
            seen.add(d)
            departments.append(d)
    return sorted(departments)


@router.get("/{course_code}", response_model=CourseDetail)
def get_course(course_code: str):
    """
    Return a single course with aggregated stats across all its sections.
    course_code should be URL-encoded if it contains spaces e.g. ACCT%202102
    """
    client = get_client()

    # Normalise — allow both "ACCT2102" and "ACCT 2102"
    code = course_code.upper().replace("%20", " ")
    if " " not in code and len(code) > 4:
        # Insert space between letters and numbers if missing
        import re
        code = re.sub(r"([A-Z]+)(\d)", r"\1 \2", code)

    course_result = (
        client.table("courses")
        .select("id, course_code, department, course_number, title")
        .eq("course_code", code)
        .single()
        .execute()
    )

    if not course_result.data:
        raise HTTPException(status_code=404, detail=f"Course '{code}' not found")

    course = course_result.data

    # Fetch sections for this course with grade totals joined
    sections_result = (
        client.table("sections")
        .select("id, grade_letter_totals(gpa_avg, dwf_pct)")
        .eq("course_code", code)
        .eq("has_grades", True)
        .execute()
    )

    sections = sections_result.data
    total_sections = len(sections)

    # Compute averages across all sections
    gpas  = [s["grade_letter_totals"]["gpa_avg"]  for s in sections
             if s.get("grade_letter_totals") and s["grade_letter_totals"].get("gpa_avg") is not None]
    dwfs  = [s["grade_letter_totals"]["dwf_pct"]  for s in sections
             if s.get("grade_letter_totals") and s["grade_letter_totals"].get("dwf_pct") is not None]

    avg_gpa     = round(sum(gpas) / len(gpas), 3) if gpas else None
    avg_dwf_pct = round(sum(dwfs) / len(dwfs), 2) if dwfs else None

    return {
        **course,
        "total_sections": total_sections,
        "avg_gpa": avg_gpa,
        "avg_dwf_pct": avg_dwf_pct,
    }