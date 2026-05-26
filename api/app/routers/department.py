"""
/department routes
------------------
GET /department/{dept}/schedule   — course schedule table for last N semesters
GET /department/{dept}/terms      — available term codes for a department
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.database import get_client
import re

router = APIRouter(prefix="/department", tags=["department"])


# ── Response models ────────────────────────────────────────────────────────────

class ScheduleCell(BaseModel):
    term_code: str
    semester: str
    year: int
    instructors: list[str]      # anonymized labels
    avg_gpa: Optional[float]
    total_students: Optional[int]


class ScheduleRow(BaseModel):
    course_code: str
    title: Optional[str]
    course_number: Optional[str]
    terms: dict[str, ScheduleCell]   # term_code → cell


class DepartmentSchedule(BaseModel):
    department: str
    term_codes: list[str]            # ordered list of terms shown (newest first)
    term_labels: dict[str, str]      # term_code → "Fa 25" label
    rows: list[ScheduleRow]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _term_label(semester: str, year: int) -> str:
    """e.g. Fall 2025 → Fa '25"""
    abbr = {"Fall": "Fa", "Spring": "Sp", "Summer": "Su"}.get(semester, semester[:2])
    return f"{abbr} '{str(year)[2:]}"


def _anonymize_in_context(names: list[str], global_map: dict[str, str]) -> list[str]:
    """Return anonymous labels for a list of professor names using a shared map."""
    labels = []
    for name in names:
        if name not in global_map:
            n = len(global_map)
            # Convert index to A, B, ..., Z, AA, AB, ...
            letters = []
            idx = n + 1
            while idx > 0:
                idx, r = divmod(idx - 1, 26)
                letters.append(chr(65 + r))
            global_map[name] = "Instructor " + "".join(reversed(letters))
        labels.append(global_map[name])
    return labels


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/{dept}/schedule", response_model=DepartmentSchedule)
def department_schedule(
    dept: str,
    terms: int = Query(4, ge=1, le=12, description="Number of most recent semesters to show"),
):
    """
    Returns a pivot table of courses × semesters for a department.
    Each cell contains the instructor labels and avg GPA for that section.
    Professor names are anonymized — consistent within this response.
    """
    client = get_client()
    dept = dept.upper()

    # ── 1. Get the N most recent term codes for this department ───────────────
    terms_result = (
        client.table("sections")
        .select("term_code, semester, year")
        .ilike("course_code", f"{dept}%")
        .eq("has_grades", True)
        .order("term_code", desc=True)
        .execute()
    )

    if not terms_result.data:
        raise HTTPException(status_code=404, detail=f"No data found for department '{dept}'")

    # Deduplicate and take the N most recent
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

    # ── 2. Fetch all sections for those terms ─────────────────────────────────
    sections_result = (
        client.table("sections")
        .select(
            "course_code, term_code, semester, year, professor_name, total, "
            "grade_letter_totals(gpa_avg)"
        )
        .ilike("course_code", f"{dept}%")
        .in_("term_code", recent_terms)
        .eq("has_grades", True)
        .order("course_code")
        .execute()
    )

    # ── 3. Fetch course titles ────────────────────────────────────────────────
    courses_result = (
        client.table("courses")
        .select("course_code, title, course_number")
        .ilike("course_code", f"{dept}%")
        .execute()
    )
    course_meta: dict[str, dict] = {
        r["course_code"]: r for r in (courses_result.data or [])
    }

    # ── 4. Build pivot table ──────────────────────────────────────────────────
    # course_code → term_code → list of sections
    pivot: dict[str, dict[str, list]] = {}
    for section in sections_result.data:
        cc = section["course_code"]
        tc = section["term_code"]
        if cc not in pivot:
            pivot[cc] = {}
        if tc not in pivot[cc]:
            pivot[cc][tc] = []
        pivot[cc][tc].append(section)

    # ── 5. Anonymize professors consistently across whole response ────────────
    prof_map: dict[str, str] = {}

    rows: list[ScheduleRow] = []
    for course_code in sorted(pivot.keys()):
        meta = course_meta.get(course_code, {})
        term_cells: dict[str, ScheduleCell] = {}

        for tc in recent_terms:
            if tc not in pivot[course_code]:
                continue

            sections_in_cell = pivot[course_code][tc]
            raw_names = list({
                s["professor_name"] for s in sections_in_cell
                if s.get("professor_name")
            })
            labels = _anonymize_in_context(raw_names, prof_map)

            gpas = [
                s["grade_letter_totals"]["gpa_avg"]
                for s in sections_in_cell
                if s.get("grade_letter_totals") and s["grade_letter_totals"].get("gpa_avg") is not None
            ]
            avg_gpa = round(sum(gpas) / len(gpas), 2) if gpas else None
            total_students = sum(s.get("total") or 0 for s in sections_in_cell)

            first = sections_in_cell[0]
            term_cells[tc] = ScheduleCell(
                term_code=tc,
                semester=first["semester"],
                year=first["year"],
                instructors=sorted(labels),
                avg_gpa=avg_gpa,
                total_students=total_students if total_students > 0 else None,
            )

        if term_cells:
            rows.append(ScheduleRow(
                course_code=course_code,
                title=meta.get("title"),
                course_number=meta.get("course_number"),
                terms=term_cells,
            ))

    return DepartmentSchedule(
        department=dept,
        term_codes=recent_terms,
        term_labels=term_labels,
        rows=rows,
    )


@router.get("/{dept}/terms", response_model=list[dict])
def department_terms(dept: str):
    """Return all available term codes for a department, newest first."""
    client = get_client()
    result = (
        client.table("sections")
        .select("term_code, semester, year")
        .ilike("course_code", f"{dept.upper()}%")
        .eq("has_grades", True)
        .order("term_code", desc=True)
        .execute()
    )
    seen: dict[str, dict] = {}
    for row in result.data:
        tc = row["term_code"]
        if tc not in seen:
            seen[tc] = {
                "term_code": tc,
                "semester": row["semester"],
                "year": row["year"],
                "label": _term_label(row["semester"], row["year"]),
            }
    return list(seen.values())