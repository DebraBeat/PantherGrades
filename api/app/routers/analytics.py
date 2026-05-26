"""
/analytics routes
-----------------
Free tier:
  GET /analytics/course/{course_code}/summary     — avg GPA, DWF, vs dept average
  GET /analytics/course/{course_code}/trend        — semester-by-semester GPA trend

Pro tier:
  GET /analytics/course/{course_code}/instructors  — per-instructor breakdown (anonymized names shown as labels)
  GET /analytics/course/{course_code}/difficulty   — difficulty score + percentile in dept
  GET /analytics/department/{dept}/overview        — dept-wide GPA distribution and hardest/easiest courses
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.database import get_client
from app.auth import get_user_tier, require_pro

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ── Response models ────────────────────────────────────────────────────────────

class CourseSummary(BaseModel):
    course_code: str
    department: str
    total_sections: int
    total_students: int
    avg_gpa: Optional[float]
    dept_avg_gpa: Optional[float]
    gpa_vs_dept: Optional[float]        # positive = easier than dept avg
    avg_dwf_pct: Optional[float]
    dept_avg_dwf_pct: Optional[float]
    pct_online: Optional[float]
    pct_in_person: Optional[float]


class TrendPoint(BaseModel):
    semester: str
    year: int
    term_code: str
    avg_gpa: Optional[float]
    avg_dwf_pct: Optional[float]
    total_students: int
    section_count: int


class InstructorBreakdown(BaseModel):
    label: str                          # "Instructor A" or real name for pro
    is_anonymous: bool
    section_count: int
    total_students: int
    avg_gpa: Optional[float]
    avg_dwf_pct: Optional[float]
    gpa_vs_course_avg: Optional[float]  # how this instructor compares to course mean


class DifficultyScore(BaseModel):
    course_code: str
    difficulty_score: float             # 0–100, higher = harder
    dept_percentile: float              # e.g. 82 means harder than 82% of dept courses
    avg_gpa: Optional[float]
    avg_dwf_pct: Optional[float]
    dept_avg_gpa: Optional[float]


class DeptCourse(BaseModel):
    course_code: str
    avg_gpa: Optional[float]
    avg_dwf_pct: Optional[float]
    total_sections: int
    difficulty_score: float


class DeptOverview(BaseModel):
    department: str
    total_courses: int
    total_sections: int
    avg_gpa: Optional[float]
    avg_dwf_pct: Optional[float]
    hardest_courses: list[DeptCourse]
    easiest_courses: list[DeptCourse]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _weighted_avg(values: list[float], weights: list[int]) -> Optional[float]:
    """Weighted average — weights are student counts."""
    total_w = sum(weights)
    if total_w == 0:
        return None
    return round(sum(v * w for v, w in zip(values, weights)) / total_w, 3)


def _difficulty_score(avg_gpa: Optional[float], avg_dwf: Optional[float]) -> float:
    """
    Simple composite difficulty score on a 0–100 scale.
    Higher = harder. Weighted 70% GPA component, 30% DWF component.
    GPA component: (4.33 - gpa) / 4.33 * 100
    DWF component: dwf_pct (already 0–100)
    """
    gpa_score = ((4.33 - (avg_gpa or 3.0)) / 4.33) * 100
    dwf_score = avg_dwf or 0
    return round(gpa_score * 0.7 + dwf_score * 0.3, 1)


def _fetch_course_sections(client, course_code: str) -> list[dict]:
    """Fetch all graded sections for a course with grade letter totals."""
    result = (
        client.table("sections")
        .select(
            "id, crn, term_code, semester, year, total, instruction_method, professor_name, "
            "grade_letter_totals(gpa_avg, dwf_pct, grade_a, grade_b, grade_c, grade_d, grade_f, wf, w)"
        )
        .eq("course_code", course_code)
        .eq("has_grades", True)
        .order("year")
        .order("semester")
        .execute()
    )
    return result.data or []


def _fetch_dept_sections(client, department: str) -> list[dict]:
    """Fetch all graded sections for a department."""
    result = (
        client.table("sections")
        .select(
            "course_code, total, "
            "grade_letter_totals(gpa_avg, dwf_pct)"
        )
        .ilike("course_code", f"{department.upper()}%")
        .eq("has_grades", True)
        .execute()
    )
    return result.data or []


# ── Free routes ────────────────────────────────────────────────────────────────

@router.get("/course/{course_code}/summary", response_model=CourseSummary)
def course_summary(course_code: str):
    """
    High-level course snapshot: avg GPA, DWF rate, and comparison
    to the department average. Available to all users.
    """
    client = get_client()
    code = course_code.upper().replace("-", " ")

    # Get department from course — fall back to parsing code if not in catalog
    import re as _re
    try:
        course_result = (
            client.table("courses")
            .select("department")
            .eq("course_code", code)
            .maybe_single()
            .execute()
        )
        dept = course_result.data["department"] if course_result.data else None
    except Exception:
        dept = None

    if not dept:
        m = _re.match(r"([A-Z]+)", code)
        dept = m.group(1) if m else code.split()[0]

    # Fetch this course's sections
    sections = _fetch_course_sections(client, code)
    if not sections:
        raise HTTPException(status_code=404, detail=f"No graded sections found for '{code}'")

    gpas, dwfs, totals = [], [], []
    online, in_person = 0, 0
    for s in sections:
        glt = s.get("grade_letter_totals") or {}
        t = s.get("total") or 0
        if glt.get("gpa_avg") is not None:
            gpas.append(glt["gpa_avg"])
            totals.append(t)
        if glt.get("dwf_pct") is not None:
            dwfs.append(glt["dwf_pct"])
        method = s.get("instruction_method", "")
        if method == "online":
            online += 1
        elif method == "in_person":
            in_person += 1

    avg_gpa = _weighted_avg(gpas, totals) if gpas else None
    avg_dwf = round(sum(dwfs) / len(dwfs), 2) if dwfs else None
    total_students = sum(totals)
    total_sections = len(sections)
    total_sections_nonzero = total_sections or 1

    # Department averages (all courses in dept)
    dept_sections = _fetch_dept_sections(client, dept)
    dept_gpas, dept_dwfs, dept_totals = [], [], []
    for s in dept_sections:
        glt = s.get("grade_letter_totals") or {}
        t = s.get("total") or 0
        if glt.get("gpa_avg") is not None:
            dept_gpas.append(glt["gpa_avg"])
            dept_totals.append(t)
        if glt.get("dwf_pct") is not None:
            dept_dwfs.append(glt["dwf_pct"])

    dept_avg_gpa = _weighted_avg(dept_gpas, dept_totals) if dept_gpas else None
    dept_avg_dwf = round(sum(dept_dwfs) / len(dept_dwfs), 2) if dept_dwfs else None

    gpa_vs_dept = (
        round(avg_gpa - dept_avg_gpa, 3)
        if avg_gpa is not None and dept_avg_gpa is not None
        else None
    )

    return {
        "course_code": code,
        "department": dept,
        "total_sections": total_sections,
        "total_students": total_students,
        "avg_gpa": avg_gpa,
        "dept_avg_gpa": dept_avg_gpa,
        "gpa_vs_dept": gpa_vs_dept,
        "avg_dwf_pct": avg_dwf,
        "dept_avg_dwf_pct": dept_avg_dwf,
        "pct_online": round(online / total_sections_nonzero * 100, 1),
        "pct_in_person": round(in_person / total_sections_nonzero * 100, 1),
    }


@router.get("/course/{course_code}/trend", response_model=list[TrendPoint])
def course_trend(course_code: str):
    """
    Semester-by-semester GPA and DWF trend for a course.
    Available to all users — this is a core free feature.
    """
    client = get_client()
    code = course_code.upper().replace("-", " ")
    sections = _fetch_course_sections(client, code)

    if not sections:
        raise HTTPException(status_code=404, detail=f"No graded sections found for '{code}'")

    # Group by term_code
    from collections import defaultdict
    term_groups: dict[str, list] = defaultdict(list)
    for s in sections:
        term_groups[s["term_code"]].append(s)

    trend = []
    for term_code in sorted(term_groups.keys()):
        group = term_groups[term_code]
        gpas, dwfs, totals = [], [], []
        for s in group:
            glt = s.get("grade_letter_totals") or {}
            t = s.get("total") or 0
            if glt.get("gpa_avg") is not None:
                gpas.append(glt["gpa_avg"])
                totals.append(t)
            if glt.get("dwf_pct") is not None:
                dwfs.append(glt["dwf_pct"])

        trend.append({
            "semester": group[0]["semester"],
            "year": group[0]["year"],
            "term_code": term_code,
            "avg_gpa": _weighted_avg(gpas, totals) if gpas else None,
            "avg_dwf_pct": round(sum(dwfs) / len(dwfs), 2) if dwfs else None,
            "total_students": sum(totals),
            "section_count": len(group),
        })

    return trend


# ── Pro routes ─────────────────────────────────────────────────────────────────

@router.get("/course/{course_code}/instructors", response_model=list[InstructorBreakdown])
def course_instructors(
    course_code: str,
    tier: str = Depends(get_user_tier),
):
    """
    Per-instructor grade breakdown for a course.
    Free users see anonymized labels. Pro users see real names.
    The comparison vs course average is available to all tiers
    since it doesn't reveal identity beyond the anonymous label.
    """
    client = get_client()
    code = course_code.upper().replace("-", " ")
    sections = _fetch_course_sections(client, code)

    if not sections:
        raise HTTPException(status_code=404, detail=f"No graded sections found for '{code}'")

    # Group by professor
    from collections import defaultdict
    prof_groups: dict[str, list] = defaultdict(list)
    for s in sections:
        name = s.get("professor_name") or "Unknown"
        prof_groups[name].append(s)

    # Compute course-wide avg GPA for comparison
    all_gpas, all_totals = [], []
    for s in sections:
        glt = s.get("grade_letter_totals") or {}
        t = s.get("total") or 0
        if glt.get("gpa_avg") is not None:
            all_gpas.append(glt["gpa_avg"])
            all_totals.append(t)
    course_avg_gpa = _weighted_avg(all_gpas, all_totals)

    # Build label map for anonymization
    prof_names = sorted(prof_groups.keys())
    from routers.sections import _index_to_label
    label_map = {
        name: _index_to_label(i) if tier != "pro" else name
        for i, name in enumerate(prof_names)
    }

    results = []
    for name, group in prof_groups.items():
        gpas, dwfs, totals = [], [], []
        for s in group:
            glt = s.get("grade_letter_totals") or {}
            t = s.get("total") or 0
            if glt.get("gpa_avg") is not None:
                gpas.append(glt["gpa_avg"])
                totals.append(t)
            if glt.get("dwf_pct") is not None:
                dwfs.append(glt["dwf_pct"])

        avg_gpa = _weighted_avg(gpas, totals)
        gpa_vs_course = (
            round(avg_gpa - course_avg_gpa, 3)
            if avg_gpa is not None and course_avg_gpa is not None
            else None
        )

        results.append({
            "label": label_map[name],
            "is_anonymous": tier != "pro",
            "section_count": len(group),
            "total_students": sum(totals),
            "avg_gpa": avg_gpa,
            "avg_dwf_pct": round(sum(dwfs) / len(dwfs), 2) if dwfs else None,
            "gpa_vs_course_avg": gpa_vs_course,
        })

    # Sort by avg_gpa descending
    results.sort(key=lambda x: x["avg_gpa"] or 0, reverse=True)
    return results


@router.get("/course/{course_code}/difficulty", response_model=DifficultyScore)
def course_difficulty(
    course_code: str,
    _: str = Depends(require_pro),
):
    """
    Composite difficulty score and department percentile ranking.
    Pro only.
    """
    client = get_client()
    code = course_code.upper().replace("-", " ")

    course_result = (
        client.table("courses").select("department").eq("course_code", code).single().execute()
    )
    if not course_result.data:
        raise HTTPException(status_code=404, detail=f"Course '{code}' not found")

    dept = course_result.data["department"]
    sections = _fetch_course_sections(client, code)

    if not sections:
        raise HTTPException(status_code=404, detail=f"No graded sections for '{code}'")

    gpas, dwfs, totals = [], [], []
    for s in sections:
        glt = s.get("grade_letter_totals") or {}
        t = s.get("total") or 0
        if glt.get("gpa_avg") is not None:
            gpas.append(glt["gpa_avg"])
            totals.append(t)
        if glt.get("dwf_pct") is not None:
            dwfs.append(glt["dwf_pct"])

    avg_gpa = _weighted_avg(gpas, totals)
    avg_dwf = round(sum(dwfs) / len(dwfs), 2) if dwfs else None
    score = _difficulty_score(avg_gpa, avg_dwf)

    # Compute scores for all courses in dept to find percentile
    dept_sections = _fetch_dept_sections(client, dept)
    dept_course_scores: dict[str, list] = {}
    for s in dept_sections:
        cc = s["course_code"]
        glt = s.get("grade_letter_totals") or {}
        if cc not in dept_course_scores:
            dept_course_scores[cc] = {"gpas": [], "dwfs": [], "totals": []}
        t = s.get("total") or 0
        if glt.get("gpa_avg") is not None:
            dept_course_scores[cc]["gpas"].append(glt["gpa_avg"])
            dept_course_scores[cc]["totals"].append(t)
        if glt.get("dwf_pct") is not None:
            dept_course_scores[cc]["dwfs"].append(glt["dwf_pct"])

    all_scores = []
    dept_gpas_all, dept_totals_all = [], []
    for cc, data in dept_course_scores.items():
        cc_gpa = _weighted_avg(data["gpas"], data["totals"])
        cc_dwf = round(sum(data["dwfs"]) / len(data["dwfs"]), 2) if data["dwfs"] else None
        all_scores.append(_difficulty_score(cc_gpa, cc_dwf))
        if cc_gpa is not None:
            dept_gpas_all.extend(data["gpas"])
            dept_totals_all.extend(data["totals"])

    dept_avg_gpa = _weighted_avg(dept_gpas_all, dept_totals_all)
    percentile = round(sum(s < score for s in all_scores) / len(all_scores) * 100, 1) if all_scores else 50.0

    return {
        "course_code": code,
        "difficulty_score": score,
        "dept_percentile": percentile,
        "avg_gpa": avg_gpa,
        "avg_dwf_pct": avg_dwf,
        "dept_avg_gpa": dept_avg_gpa,
    }


@router.get("/department/{department}/overview", response_model=DeptOverview)
def department_overview(
    department: str,
    top_n: int = Query(5, ge=1, le=20, description="Number of hardest/easiest courses to return"),
    _: str = Depends(require_pro),
):
    """
    Department-wide overview with hardest and easiest courses.
    Pro only.
    """
    client = get_client()
    dept = department.upper()

    dept_sections = _fetch_dept_sections(client, dept)
    if not dept_sections:
        raise HTTPException(status_code=404, detail=f"No data found for department '{dept}'")

    # Aggregate per course
    from collections import defaultdict
    course_data: dict[str, dict] = defaultdict(lambda: {"gpas": [], "dwfs": [], "totals": [], "sections": 0})
    for s in dept_sections:
        cc = s["course_code"]
        glt = s.get("grade_letter_totals") or {}
        t = s.get("total") or 0
        course_data[cc]["sections"] += 1
        if glt.get("gpa_avg") is not None:
            course_data[cc]["gpas"].append(glt["gpa_avg"])
            course_data[cc]["totals"].append(t)
        if glt.get("dwf_pct") is not None:
            course_data[cc]["dwfs"].append(glt["dwf_pct"])

    courses = []
    all_gpas, all_totals = [], []
    for cc, data in course_data.items():
        avg_gpa = _weighted_avg(data["gpas"], data["totals"])
        avg_dwf = round(sum(data["dwfs"]) / len(data["dwfs"]), 2) if data["dwfs"] else None
        score = _difficulty_score(avg_gpa, avg_dwf)
        courses.append({
            "course_code": cc,
            "avg_gpa": avg_gpa,
            "avg_dwf_pct": avg_dwf,
            "total_sections": data["sections"],
            "difficulty_score": score,
        })
        if avg_gpa is not None:
            all_gpas.extend(data["gpas"])
            all_totals.extend(data["totals"])

    courses.sort(key=lambda x: x["difficulty_score"], reverse=True)

    return {
        "department": dept,
        "total_courses": len(courses),
        "total_sections": len(dept_sections),
        "avg_gpa": _weighted_avg(all_gpas, all_totals),
        "avg_dwf_pct": round(
            sum(c["avg_dwf_pct"] for c in courses if c["avg_dwf_pct"] is not None) /
            max(sum(1 for c in courses if c["avg_dwf_pct"] is not None), 1), 2
        ),
        "hardest_courses": courses[:top_n],
        "easiest_courses": list(reversed(courses))[:top_n],
    }