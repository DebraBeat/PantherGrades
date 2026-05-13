"""
/sections routes
----------------
GET /sections                          — paginated list with filters
GET /sections/{crn}/{term_code}        — single section with full grade breakdown
GET /sections/by-course/{course_code}  — all sections for a course
GET /sections/by-professor/{label}     — all sections for an anonymized professor label

Professor anonymization
-----------------------
Free users see professors labelled "Instructor A", "Instructor B", etc.
Labels are assigned deterministically per course so the same professor
always gets the same label within a given course page — but the label
is NOT consistent across courses, preventing cross-course identification.

Pro users see real professor names.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.database import get_client
from app.auth import get_user_tier

router = APIRouter(prefix="/sections", tags=["sections"])


# ── Response models ────────────────────────────────────────────────────────────

class GradeLetterTotals(BaseModel):
    grade_a: Optional[int]
    grade_b: Optional[int]
    grade_c: Optional[int]
    grade_d: Optional[int]
    grade_f: Optional[int]
    wf: Optional[int]
    w: Optional[int]
    other: Optional[int]
    gpa_avg: Optional[float]
    dwf_pct: Optional[float]


class GradeGranular(BaseModel):
    a_plus: Optional[int]
    a: Optional[int]
    a_minus: Optional[int]
    b_plus: Optional[int]
    b: Optional[int]
    b_minus: Optional[int]
    c_plus: Optional[int]
    c: Optional[int]
    c_minus: Optional[int]
    d: Optional[int]
    f: Optional[int]
    wf: Optional[int]
    w: Optional[int]


class ProfessorInfo(BaseModel):
    label: str                  # Always present — "Instructor A" or real name
    is_anonymous: bool          # True for free users
    department: Optional[str]


class Section(BaseModel):
    id: str
    crn: str
    term_code: str
    semester: Optional[str]
    year: Optional[int]
    course_code: Optional[str]
    total: Optional[int]
    instruction_method: Optional[str]
    has_grades: Optional[bool]
    professor: Optional[ProfessorInfo]
    grade_letter_totals: Optional[GradeLetterTotals]


class SectionDetail(Section):
    grade_granular: Optional[GradeGranular]


# ── Professor anonymization ────────────────────────────────────────────────────

def _index_to_label(n: int) -> str:
    """Converts index → Instructor A, B, ..., Z, AA, AB, ..."""
    letters = []
    n += 1
    while n > 0:
        n, r = divmod(n - 1, 26)
        letters.append(chr(65 + r))
    return "Instructor " + "".join(reversed(letters))


def anonymize_professors(sections: list[dict]) -> list[dict]:
    """
    Assign consistent anonymous labels scoped to this set of sections.
    Same professor → same label within the response.
    Labels are NOT consistent across different course pages by design.
    """
    prof_to_label: dict[str, str] = {}
    for section in sections:
        prof_raw = section.get("_prof_raw")
        if not prof_raw:
            continue
        name = prof_raw.get("name") or "Unknown"
        if name not in prof_to_label:
            prof_to_label[name] = _index_to_label(len(prof_to_label))
        section["professor"] = {
            "label": prof_to_label[name],
            "is_anonymous": True,
            "department": prof_raw.get("department"),
        }
    return sections


def reveal_professors(sections: list[dict]) -> list[dict]:
    """Pro users — use real professor names as the label."""
    for section in sections:
        prof_raw = section.get("_prof_raw")
        if not prof_raw:
            continue
        section["professor"] = {
            "label": prof_raw.get("name") or "Unknown",
            "is_anonymous": False,
            "department": prof_raw.get("department"),
        }
    return sections


def apply_professor_visibility(sections: list[dict], tier: str) -> list[dict]:
    sections = reveal_professors(sections) if tier == "pro" else anonymize_professors(sections)
    for s in sections:
        s.pop("_prof_raw", None)
    return sections


# ── Query helpers ──────────────────────────────────────────────────────────────

def _build_section_query(client, include_granular: bool = False):
    granular_select = ", grade_granular(*)" if include_granular else ""
    return client.table("sections").select(
        f"id, crn, term_code, semester, year, course_code, total, "
        f"instruction_method, has_grades, "
        f"professors(name, department), "
        f"grade_letter_totals(grade_a, grade_b, grade_c, grade_d, grade_f, "
        f"wf, w, other, gpa_avg, dwf_pct)"
        f"{granular_select}"
    )


def _extract_prof(row: dict) -> dict:
    """Lift nested professors object into _prof_raw for uniform processing."""
    row["_prof_raw"] = row.pop("professors", None)
    row.setdefault("professor", None)
    return row


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[Section])
def list_sections(
    course_code: Optional[str] = Query(None),
    department: Optional[str]  = Query(None),
    semester: Optional[str]    = Query(None, description="Fall | Spring | Summer"),
    year: Optional[int]        = Query(None),
    instruction_method: Optional[str] = Query(None),
    has_grades: Optional[bool] = Query(None),
    limit: int  = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tier: str   = Depends(get_user_tier),
):
    """Paginated list of sections with optional filters."""
    client = get_client()
    query = _build_section_query(client)
    if course_code:
        query = query.eq("course_code", course_code.upper())
    if department:
        query = query.ilike("course_code", f"{department.upper()}%")
    if semester:
        query = query.eq("semester", semester.capitalize())
    if year:
        query = query.eq("year", year)
    if instruction_method:
        query = query.eq("instruction_method", instruction_method)
    if has_grades is not None:
        query = query.eq("has_grades", has_grades)
    result = query.order("year", desc=True).order("semester").range(offset, offset + limit - 1).execute()
    sections = [_extract_prof(row) for row in result.data]
    return apply_professor_visibility(sections, tier)


@router.get("/by-course/{course_code}", response_model=list[Section])
def sections_by_course(
    course_code: str,
    year: Optional[int]      = Query(None),
    semester: Optional[str]  = Query(None),
    tier: str                = Depends(get_user_tier),
):
    """
    All sections for a course, newest first.
    Primary endpoint for the course detail page.
    Professor labels are consistent within this response.
    """
    client = get_client()
    code = course_code.upper().replace("-", " ")
    query = (
        _build_section_query(client)
        .eq("course_code", code)
        .order("year", desc=True)
        .order("semester")
    )
    if year:
        query = query.eq("year", year)
    if semester:
        query = query.eq("semester", semester.capitalize())
    result = query.execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"No sections found for '{code}'")
    sections = [_extract_prof(row) for row in result.data]
    return apply_professor_visibility(sections, tier)


@router.get("/by-professor/{label}", response_model=list[Section])
def sections_by_professor(
    label: str,
    course_code: Optional[str] = Query(None),
    year: Optional[int]        = Query(None),
    tier: str                  = Depends(get_user_tier),
):
    """
    Pro only — fetch all sections by a real professor name.
    Free users get 402 since anonymous labels are course-scoped
    and cannot be used to query across courses.
    """
    if tier != "pro":
        raise HTTPException(
            status_code=402,
            detail={
                "error": "pro_required",
                "message": "Viewing all sections by a specific instructor requires PantherGrades Pro.",
                "upgrade_url": "/subscribe",
            },
        )
    client = get_client()
    name = label.replace("%2C", ",").replace("%20", " ")
    query = (
        _build_section_query(client)
        .eq("professor_name", name)
        .order("year", desc=True)
        .order("course_code")
    )
    if course_code:
        query = query.eq("course_code", course_code.upper())
    if year:
        query = query.eq("year", year)
    result = query.execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"No sections found for '{name}'")
    sections = [_extract_prof(row) for row in result.data]
    return reveal_professors(sections)


@router.get("/{crn}/{term_code}", response_model=SectionDetail)
def get_section(
    crn: str,
    term_code: str,
    tier: str = Depends(get_user_tier),
):
    """Single section detail with full grade breakdown including plus/minus grades."""
    client = get_client()
    result = (
        _build_section_query(client, include_granular=True)
        .eq("crn", crn)
        .eq("term_code", term_code)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Section {crn}/{term_code} not found")
    sections = apply_professor_visibility([_extract_prof(result.data)], tier)
    return sections[0]