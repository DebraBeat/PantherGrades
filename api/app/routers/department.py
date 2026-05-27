"""
/department routes
------------------
GET /department                      — list all departments with course counts
GET /department/{dept}/schedule      — course x semester table for last N semesters
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.database import get_client

router = APIRouter(prefix="/department", tags=["department"])


# ── Response models ────────────────────────────────────────────────────────────

class DepartmentSummary(BaseModel):
    department: str
    course_count: int


class ScheduleCell(BaseModel):
    instructors: list[str]   # real professor names
    avg_gpa: Optional[float]


class ScheduleRow(BaseModel):
    course_code: str
    title: Optional[str]
    terms: dict[str, Optional[ScheduleCell]]


class DepartmentSchedule(BaseModel):
    department: str
    term_codes: list[str]
    term_labels: dict[str, str]
    rows: list[ScheduleRow]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _term_label(semester: str, year: int) -> str:
    abbr = {"Fall": "Fa", "Spring": "Sp", "Summer": "Su"}.get(semester, semester[:2])
    return f"{abbr} '{str(year)[2:]}"


def _make_label(n: int) -> str:
    letters = []
    idx = n + 1
    while idx > 0:
        idx, r = divmod(idx - 1, 26)
        letters.append(chr(65 + r))
    return "Instructor " + "".join(reversed(letters))


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[DepartmentSummary])
def list_departments_route():
    """All departments with number of courses, sorted alphabetically."""
    client = get_client()
    result = (
        client.table("courses")
        .select("department")
        .not_.is_("department", "null")
        .execute()
    )
    counts: dict[str, int] = {}
    for row in result.data:
        d = row["department"]
        if d:
            counts[d] = counts.get(d, 0) + 1
    return [
        {"department": d, "course_count": c}
        for d, c in sorted(counts.items())
    ]


@router.get("/{dept}/schedule", response_model=DepartmentSchedule)
def department_schedule(
    dept: str,
    terms: int = Query(10, ge=1, le=20, description="Number of most recent semesters"),
):
    """
    Course x semester pivot table for a department.
    Cells list anonymized instructor labels, or None (Not offered).
    Labels are consistent within the whole response.
    """
    client = get_client()
    dept = dept.upper()

    # 1. Get N most recent term codes for this dept
    terms_result = (
        client.table("sections")
        .select("term_code, semester, year")
        .ilike("course_code", f"{dept}%")
        .eq("has_grades", True)
        .order("term_code", desc=True)
        .execute()
    )
    if not terms_result.data:
        raise HTTPException(status_code=404, detail=f"No data for department '{dept}'")

    seen_terms: dict[str, dict] = {}
    for row in terms_result.data:
        tc = row["term_code"]
        if tc not in seen_terms:
            seen_terms[tc] = {"semester": row["semester"], "year": row["year"]}

    recent_terms = sorted(seen_terms.keys(), reverse=True)[:terms]
    term_labels = {
        tc: _term_label(seen_terms[tc]["semester"], seen_terms[tc]["year"])
        for tc in recent_terms
    }

    # 2. Fetch all sections in those terms
    sections_result = (
        client.table("sections")
        .select("course_code, term_code, professor_name, grade_letter_totals(gpa_avg)")
        .ilike("course_code", f"{dept}%")
        .in_("term_code", recent_terms)
        .eq("has_grades", True)
        .execute()
    )

    # 3. Fetch course titles
    courses_result = (
        client.table("courses")
        .select("course_code, title")
        .ilike("course_code", f"{dept}%")
        .execute()
    )
    course_titles: dict[str, Optional[str]] = {
        r["course_code"]: r.get("title") for r in (courses_result.data or [])
    }

    # 4. Build pivot
    pivot: dict[str, dict[str, list]] = {}
    all_courses: set[str] = set(course_titles.keys())

    for section in sections_result.data:
        cc = section["course_code"]
        tc = section["term_code"]
        all_courses.add(cc)
        pivot.setdefault(cc, {}).setdefault(tc, []).append(section)

    # 5. Build rows with real professor names
    rows: list[ScheduleRow] = []

    for course_code in sorted(all_courses):
        term_cells: dict[str, Optional[ScheduleCell]] = {}

        for tc in recent_terms:
            cell_sections = (pivot.get(course_code) or {}).get(tc, [])
            if not cell_sections:
                term_cells[tc] = None
                continue

            # Use real names directly — no anonymization
            names = sorted({
                s["professor_name"] for s in cell_sections if s.get("professor_name")
            })

            gpas = [
                s["grade_letter_totals"]["gpa_avg"]
                for s in cell_sections
                if s.get("grade_letter_totals") and s["grade_letter_totals"].get("gpa_avg") is not None
            ]
            term_cells[tc] = ScheduleCell(
                instructors=names,
                avg_gpa=round(sum(gpas) / len(gpas), 2) if gpas else None,
            )

        rows.append(ScheduleRow(
            course_code=course_code,
            title=course_titles.get(course_code),
            terms=term_cells,
        ))

    return DepartmentSchedule(
        department=dept,
        term_codes=recent_terms,
        term_labels=term_labels,
        rows=rows,
    )