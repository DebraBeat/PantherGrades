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
    id: Optional[str]
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
    q: str = Query(..., min_length=2, description="Search term — course code or title"),
    limit: int = Query(20, ge=1, le=50),
):
    """
    Search courses by course code prefix or title keyword.
    e.g. /courses/search?q=ACCT returns all accounting courses.
    e.g. /courses/search?q=principles returns courses with that word in the title.
    """
    client = get_client()
    select = "id, course_code, department, course_number, title"

    # 1. Try exact course code prefix first (e.g. "BIOL 1")
    result = (
        client.table("courses")
        .select(select)
        .ilike("course_code", f"{q.upper()}%")
        .order("course_code")
        .limit(limit)
        .execute()
    )
    if result.data:
        return result.data

    # 2. Try title keyword search (e.g. "principles of programming")
    result = (
        client.table("courses")
        .select(select)
        .ilike("title", f"%{q}%")
        .order("course_code")
        .limit(limit)
        .execute()
    )
    if result.data:
        return result.data

    # 3. Fall back to course_code contains search
    result = (
        client.table("courses")
        .select(select)
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

    try:
        course_result = (
            client.table("courses")
            .select("id, course_code, department, course_number, title")
            .eq("course_code", code)
            .maybe_single()
            .execute()
        )
        course = course_result.data if course_result else None
    except Exception:
        course = None

    if not course:
        # Course missing from catalog — synthesize a minimal record from sections
        dept = re.match(r"([A-Z]+)", code)
        course = {
            "id": None,
            "course_code": code,
            "department": dept.group(1) if dept else None,
            "course_number": code.split()[-1] if " " in code else None,
            "title": None,
        }

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