"""
PantherGrades — Grade Distribution Prediction Model
====================================================
Computes expected grade distributions for every course using
exponentially-weighted historical data. Results are stored in
the course_predictions table in Supabase.

Model overview
--------------
For each course (and instruction method), we:
1. Fetch all historical graded sections
2. Weight each section by recency using exponential decay:
     weight = 2^(-(age_in_semesters / halflife))
   where halflife = 4 semesters (2 years) by default
3. Compute weighted mean grade proportions
4. Assign confidence based on effective sample size (ESS)

Confidence thresholds:
  high   — ESS >= 500 students  (well-sampled course)
  medium — ESS >= 100 students
  low    — ESS <  100 students  (few sections, treat with caution)

Usage
-----
  pip install pandas supabase python-dotenv
  python3 predict.py --dry-run         # compute only, no DB writes
  python3 predict.py                   # full run
  python3 predict.py --course BIOL 1103  # single course
  python3 predict.py --halflife 6      # slower decay (3 years)
"""

import argparse
import logging
import os
from collections import defaultdict
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("predict")

# ── Constants ──────────────────────────────────────────────────────────────────
DEFAULT_HALFLIFE = 4          # semesters
CONFIDENCE_HIGH   = 500       # effective students
CONFIDENCE_MEDIUM = 100

# GPA weights for letter grades (using GSU's 4.33 scale)
GPA_WEIGHTS = {
    "grade_a": 4.0,   # A  (we don't have A+ separately in letter totals)
    "grade_b": 3.0,
    "grade_c": 2.0,
    "grade_d": 1.0,
    "grade_f": 0.0,
    "wf":      0.0,
}


# ── Data fetching ──────────────────────────────────────────────────────────────

def fetch_all_sections(client) -> pd.DataFrame:
    """Fetch all graded sections with grade letter totals."""
    log.info("Fetching sections from Supabase...")

    all_rows = []
    page_size = 1000
    offset = 0

    while True:
        result = (
            client.table("sections")
            .select(
                "course_code, term_code, semester, year, instruction_method, total, "
                "grade_letter_totals(grade_a, grade_b, grade_c, grade_d, grade_f, wf, w, gpa_avg)"
            )
            .eq("has_grades", True)
            .not_.is_("course_code", "null")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = result.data
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
        offset += page_size

    log.info(f"  Fetched {len(all_rows):,} sections")

    # Flatten nested grade_letter_totals
    records = []
    for row in all_rows:
        glt = row.get("grade_letter_totals") or {}
        total = row.get("total") or 0
        if total == 0:
            continue
        records.append({
            "course_code":        row["course_code"],
            "term_code":          row["term_code"],
            "semester":           row.get("semester"),
            "year":               row.get("year"),
            "instruction_method": row.get("instruction_method") or "unknown",
            "total":              total,
            "grade_a":            glt.get("grade_a") or 0,
            "grade_b":            glt.get("grade_b") or 0,
            "grade_c":            glt.get("grade_c") or 0,
            "grade_d":            glt.get("grade_d") or 0,
            "grade_f":            glt.get("grade_f") or 0,
            "wf":                 glt.get("wf") or 0,
            "w":                  glt.get("w") or 0,
            "gpa_avg":            glt.get("gpa_avg"),
        })

    df = pd.DataFrame(records)
    log.info(f"  Usable sections: {len(df):,}")
    return df


# ── Recency weighting ──────────────────────────────────────────────────────────

def add_recency_weights(df: pd.DataFrame, halflife: int) -> pd.DataFrame:
    """
    Add a recency_weight column using exponential decay.
    Most recent term gets weight=1.0; older terms decay by half every `halflife` semesters.
    """
    # Sort term_codes chronologically and assign ordinal rank
    all_terms = sorted(df["term_code"].unique())
    term_rank = {tc: i for i, tc in enumerate(all_terms)}
    max_rank = len(all_terms) - 1

    df = df.copy()
    df["term_rank"] = df["term_code"].map(term_rank)
    df["age"] = max_rank - df["term_rank"]           # 0 = most recent
    df["recency_weight"] = 2.0 ** (-df["age"] / halflife)
    return df


# ── Prediction for one group ───────────────────────────────────────────────────

def predict_group(group: pd.DataFrame, halflife: int) -> dict:
    """
    Compute weighted grade distribution for a group of sections.
    Returns a dict with predicted proportions, GPA, and metadata.
    """
    grade_cols = ["grade_a", "grade_b", "grade_c", "grade_d", "grade_f", "wf", "w"]

    # Weight = recency_weight * total_students (size-weighted + recency-weighted)
    group = group.copy()
    group["weight"] = group["recency_weight"] * group["total"]
    total_weight = group["weight"].sum()

    if total_weight == 0:
        return None

    # Weighted proportions for each grade
    preds = {}
    for col in grade_cols:
        preds[f"pred_{col}"] = float(
            (group[col] * group["weight"]).sum() / total_weight / group["total"].mean()
            * group["total"].mean() / group["total"].mean()
        )

    # Simpler: weighted proportion = sum(count * weight) / sum(total * weight)
    # Compute raw weighted proportions
    raw_preds = {}
    for col in grade_cols:
        numerator   = (group[col]    * group["weight"]).sum()
        denominator = (group["total"] * group["weight"]).sum()
        raw_preds[col] = round(float(numerator / denominator), 4) if denominator > 0 else 0.0

    # Normalize to sum to 1.0
    total_pred = sum(raw_preds.values())
    if total_pred > 0:
        for col in grade_cols:
            raw_preds[col] = round(raw_preds[col] / total_pred, 4)

    # Map DataFrame column names → schema column names
    COL_MAP = {
        "grade_a": "pred_a",
        "grade_b": "pred_b",
        "grade_c": "pred_c",
        "grade_d": "pred_d",
        "grade_f": "pred_f",
        "wf":      "pred_wf_raw",
        "w":       "pred_w_raw",
    }
    preds = {COL_MAP[col]: raw_preds[col] for col in grade_cols}

    # Predicted GPA
    gpa_num = sum(raw_preds[col] * GPA_WEIGHTS[col] for col in GPA_WEIGHTS)
    gpa_den = sum(raw_preds[col] for col in GPA_WEIGHTS)
    pred_gpa = round(gpa_num / gpa_den, 2) if gpa_den > 0 else None

    # Effective sample size (ESS) — accounts for weighting
    # ESS = (sum of weights)^2 / sum(weights^2)
    weights = group["weight"].values
    ess_weight = (weights.sum() ** 2) / (weights ** 2).sum() if len(weights) > 1 else weights.sum()
    # Scale ESS to student count
    avg_section_size = group["total"].mean()
    ess_students = ess_weight * avg_section_size / group["weight"].mean() if group["weight"].mean() > 0 else 0

    confidence = (
        "high"   if ess_students >= CONFIDENCE_HIGH   else
        "medium" if ess_students >= CONFIDENCE_MEDIUM else
        "low"
    )

    # Merge W and WF into single pred_w
    preds["pred_w"] = round(preds.pop("pred_wf_raw", 0) + preds.pop("pred_w_raw", 0), 4)

    return {
        **preds,
        "pred_gpa":   pred_gpa,
        "n_sections": int(len(group)),
        "n_students": int(group["total"].sum()),
        "confidence": confidence,
        "latest_term": str(group["term_code"].max()),
    }


# ── Main prediction pipeline ───────────────────────────────────────────────────

def run_predictions(df: pd.DataFrame, halflife: int, course_filter: str = None) -> list[dict]:
    """
    Run predictions for all courses (or a single course if course_filter is set).
    Returns list of prediction records ready to upsert.
    """
    df = add_recency_weights(df, halflife)

    if course_filter:
        df = df[df["course_code"] == course_filter.upper()]
        if df.empty:
            log.warning(f"No sections found for course '{course_filter}'")
            return []

    courses = df["course_code"].unique()
    log.info(f"Computing predictions for {len(courses):,} courses...")

    records = []
    for course_code in courses:
        course_df = df[df["course_code"] == course_code]

        # 1. Prediction across ALL instruction methods combined
        pred_all = predict_group(course_df, halflife)
        if pred_all:
            records.append({
                "course_code": course_code,
                "instruction_method": "all",
                "decay_halflife": halflife,
                **pred_all,
            })

        # 2. Separate predictions for in_person and online if enough data
        for method in ["in_person", "online"]:
            method_df = course_df[course_df["instruction_method"] == method]
            if len(method_df) >= 2:   # need at least 2 sections
                pred = predict_group(method_df, halflife)
                if pred:
                    records.append({
                        "course_code": course_code,
                        "instruction_method": method,
                        "decay_halflife": halflife,
                        **pred,
                    })

    log.info(f"  Generated {len(records):,} prediction records")
    return records


# ── Supabase upsert ────────────────────────────────────────────────────────────

def upsert_predictions(client, records: list[dict]):
    BATCH = 500
    total = len(records)
    for i in range(0, total, BATCH):
        batch = records[i : i + BATCH]
        client.table("course_predictions").upsert(
            batch, on_conflict="course_code,instruction_method"
        ).execute()
        log.info(f"  Upserted {i + len(batch):,}/{total:,} predictions")
    log.info("Done ✓")


# ── Preview ────────────────────────────────────────────────────────────────────

def preview(records: list[dict], n: int = 10):
    print(f"\n{'Course':<15} {'Method':<12} {'A':>6} {'B':>6} {'C':>6} {'D':>6} {'F':>6} {'W':>6} {'GPA':>6} {'Conf':<8} {'N'}")
    print("-" * 95)
    for r in records[:n]:
        if r["instruction_method"] != "all":
            continue
        print(
            f"{r['course_code']:<15} {r['instruction_method']:<12} "
            f"{r.get('pred_grade_a', r.get('pred_a', 0)):>6.1%} "
            f"{r.get('pred_grade_b', r.get('pred_b', 0)):>6.1%} "
            f"{r.get('pred_grade_c', r.get('pred_c', 0)):>6.1%} "
            f"{r.get('pred_grade_d', r.get('pred_d', 0)):>6.1%} "
            f"{r.get('pred_grade_f', r.get('pred_f', 0)):>6.1%} "
            f"{r.get('pred_w', 0):>6.1%} "
            f"{r.get('pred_gpa', 0) or 0:>6.2f} "
            f"{r.get('confidence', '?'):<8} "
            f"{r.get('n_sections', 0)}"
        )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="PantherGrades prediction model")
    parser.add_argument("--dry-run",   action="store_true", help="Compute only, skip Supabase write")
    parser.add_argument("--course",    type=str, default=None, help="Run for a single course code")
    parser.add_argument("--halflife",  type=int, default=DEFAULT_HALFLIFE,
                        help=f"Recency decay half-life in semesters (default: {DEFAULT_HALFLIFE})")
    args = parser.parse_args()

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    client = create_client(url, key)

    df = fetch_all_sections(client)
    records = run_predictions(df, halflife=args.halflife, course_filter=args.course)
    preview(records)

    if args.dry_run:
        log.info("Dry run — skipping Supabase upsert")
        return

    upsert_predictions(client, records)


if __name__ == "__main__":
    main()