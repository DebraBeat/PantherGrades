"""
PantherGrades ETL Pipeline
==========================
Reads all distribution_* and granular_* CSVs from two folders,
cleans and normalizes the data, and upserts into Supabase.

Folder structure expected:
  data/
    distribution/   ← distribution_fa_05.csv, distribution_sp_06.csv, ...
    granular/       ← granular_fa_05.csv, granular_sp_06.csv, ...

Usage:
  pip install pandas supabase python-dotenv
  python pipeline.py --distribution ./data/distribution --granular ./data/granular
"""

import argparse
import logging
import os
import re
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("etl")

# ── Semester helpers ───────────────────────────────────────────────────────────
SEMESTER_MAP = {"fa": "Fall", "sp": "Spring", "su": "Summer"}

def parse_filename(path: Path) -> dict:
    """
    Extract semester and year from a filename like distribution_fa_05.csv
    Returns {"semester": "Fall", "year": 2005, "term_code": "200508"}
    """
    stem = path.stem.lower()  # e.g. "distribution_fa_05"
    match = re.search(r"_(fa|sp|su)_(\d{2})$", stem)
    if not match:
        raise ValueError(f"Cannot parse semester/year from filename: {path.name}")

    sem_code = match.group(1)
    year_short = int(match.group(2))
    year = 2000 + year_short

    semester = SEMESTER_MAP[sem_code]

    # Build a sortable term code (YYYYMM) matching GSU convention:
    # Fall = 08, Spring = 01, Summer = 05
    month = {"fa": "08", "sp": "01", "su": "05"}[sem_code]
    term_code = f"{year}{month}"

    return {"semester": semester, "year": year, "term_code": term_code}


# ── Column normalisation ───────────────────────────────────────────────────────
# Map raw CSV column names → clean internal names
DIST_COL_MAP = {
    "CRN":                  "crn",
    "Course":               "course_raw",
    "Professor":            "professor_raw",
    "A  (90-100)":          "grade_a",
    "B  (80-89)":           "grade_b",
    "C  (70-79)":           "grade_c",
    "D  (60-69)":           "grade_d",
    "F <60":                "grade_f",
    "WF":                   "wf",
    "DWF":                  "dwf_pct",
    "W":                    "w",
    "CRS AVG":              "gpa_avg",
    "Other ":               "other",
    "Other":                "other",       # handle trimmed variant
    "Total":                "total",
    "Instruction Method":   "instruction_method",
}

GRAN_COL_MAP = {
    "CRN":                  "crn",
    "A+":                   "a_plus",
    "A":                    "a",
    "A-":                   "a_minus",
    "B+":                   "b_plus",
    "B":                    "b",
    "B-":                   "b_minus",
    "C+":                   "c_plus",
    "C":                    "c",
    "C-":                   "c_minus",
    "D":                    "d",
    "F":                    "f",
    "WF":                   "wf",
    "A-WF":                 "a_minus_wf",
    "DWF":                  "dwf_pct",
    "W":                    "w",
    "Other":                "other",
    "Total":                "total",
    "Instruction Method":   "instruction_method",
}

INSTRUCTION_METHOD_MAP = {
    "T":  "in_person",
    "F":  "online",
    "H":  "hybrid",
    "P":  "web_enhanced",
    "NT": "non_traditional",
    "10": "other",
    "20": "other",
}


# ── Read + clean a single distribution CSV ────────────────────────────────────
def read_distribution(path: Path, meta: dict) -> pd.DataFrame:
    # Read everything as str to prevent pandas mis-inferring types on older files
    df = pd.read_csv(path, dtype=str)
    df.columns = df.columns.str.strip()

    # Drop A- WF before renaming — it duplicates Total and causes alignment errors
    df = df.drop(columns=["A- WF"], errors="ignore")

    # Convert numeric columns from str
    numeric_cols = [
        "A  (90-100)", "B  (80-89)", "C  (70-79)", "D  (60-69)", "F <60",
        "WF", "DWF", "W", "CRS AVG", "Other ", "Other", "Total",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Rename to internal names (only columns that exist)
    rename = {k: v for k, v in DIST_COL_MAP.items() if k in df.columns}
    df = df.rename(columns=rename)

    # Attach semester metadata
    df["semester"] = meta["semester"]
    df["year"]     = meta["year"]
    df["term_code"] = meta["term_code"]

    # Clean strings — force CRN to str in case older CSVs parsed it as int
    df["crn"]           = df["crn"].astype(str).str.strip()
    df["course_raw"]    = df["course_raw"].astype(str).str.strip()
    df["professor_raw"] = df["professor_raw"].astype(str).str.strip()

    # Split course_raw into department + course_number
    # e.g. "ACCT 2102" → dept="ACCT", course_number="2102"
    split = df["course_raw"].str.extract(r"^([A-Z]+)\s+(\S+)")
    df["department"]     = split[0]
    df["course_number"]  = split[1]

    # Normalise instruction method
    df["instruction_method"] = (
        df["instruction_method"]
        .str.strip()
        .map(INSTRUCTION_METHOD_MAP)
        .fillna("unknown")
    )

    # GPA > 4.0 is valid at GSU (A+ = 4.33) — keep as-is
    # GPA of exactly 0 with no graded students → set to null
    graded_mask = df.get("total", pd.Series(0)) > df.get("other", pd.Series(0))
    if "gpa_avg" in df.columns:
        df.loc[~graded_mask, "gpa_avg"] = None

    # Flag sections with no graded students
    df["has_grades"] = graded_mask

    return df


# ── Read + clean a single granular CSV ───────────────────────────────────────
def read_granular(path: Path, meta: dict) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"CRN": str})
    df.columns = df.columns.str.strip()

    rename = {k: v for k, v in GRAN_COL_MAP.items() if k in df.columns}
    df = df.rename(columns=rename)

    df["crn"]       = df["crn"].astype(str).str.strip()
    df["semester"]  = meta["semester"]
    df["year"]      = meta["year"]
    df["term_code"] = meta["term_code"]

    return df


# ── Load all files in a folder ─────────────────────────────────────────────────
def load_folder(folder: Path, reader_fn) -> pd.DataFrame:
    frames = []
    files = sorted(folder.glob("*.csv"))
    if not files:
        log.warning(f"No CSV files found in {folder}")
        return pd.DataFrame()

    for f in files:
        try:
            meta = parse_filename(f)
            df = reader_fn(f, meta)
            frames.append(df)
            log.info(f"  ✓  {f.name}  →  {len(df):,} rows  ({meta['semester']} {meta['year']})")
        except Exception as e:
            log.warning(f"  ✗  {f.name}  →  SKIPPED: {e}")

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# ── Derive normalised tables ──────────────────────────────────────────────────
def build_courses(dist: pd.DataFrame) -> pd.DataFrame:
    """Unique course codes."""
    return (
        dist[["course_raw", "department", "course_number"]]
        .drop_duplicates(subset=["course_raw"])
        .rename(columns={"course_raw": "course_code"})
        .reset_index(drop=True)
    )


def build_professors(dist: pd.DataFrame) -> pd.DataFrame:
    """Unique professors. name_visible defaults False (paywall flag)."""
    profs = (
        dist[["professor_raw", "department"]]
        .drop_duplicates(subset=["professor_raw"])
        .rename(columns={"professor_raw": "name"})
        .reset_index(drop=True)
    )
    profs["name_visible"] = False
    return profs


def build_sections(dist: pd.DataFrame) -> pd.DataFrame:
    """One row per CRN per semester."""
    cols = [
        "crn", "course_raw", "professor_raw",
        "semester", "year", "term_code",
        "total", "other", "instruction_method", "has_grades",
    ]
    return dist[cols].copy().rename(columns={
        "course_raw":    "course_code",
        "professor_raw": "professor_name",
    })


def build_grade_letter_totals(dist: pd.DataFrame) -> pd.DataFrame:
    grade_cols = ["grade_a", "grade_b", "grade_c", "grade_d", "grade_f",
                  "wf", "w", "other", "gpa_avg", "dwf_pct"]
    available = ["crn", "term_code"] + [c for c in grade_cols if c in dist.columns]
    return dist[available].copy()


def build_grade_granular(gran: pd.DataFrame) -> pd.DataFrame:
    grade_cols = ["a_plus", "a", "a_minus", "b_plus", "b", "b_minus",
                  "c_plus", "c", "c_minus", "d", "f", "wf", "w",
                  "other", "dwf_pct", "a_minus_wf"]
    available = ["crn", "term_code"] + [c for c in grade_cols if c in gran.columns]
    return gran[available].copy()


def attach_section_ids(client: Client, df: pd.DataFrame) -> pd.DataFrame:
    """
    Fetch all section (crn, term_code) → id mappings from Supabase and
    add a section_id column to df. Rows that cannot be matched are dropped
    with a warning (should not happen if sections were upserted first).
    """
    log.info("  Fetching section IDs from Supabase...")

    # Supabase returns max 1000 rows by default — paginate to get all
    all_rows = []
    page_size = 1000
    offset = 0
    while True:
        result = (
            client.table("sections")
            .select("id, crn, term_code")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = result.data
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
        offset += page_size

    lookup = {(r["crn"], r["term_code"]): r["id"] for r in all_rows}
    log.info(f"  Loaded {len(lookup):,} section IDs")

    df = df.copy()
    df["section_id"] = df.apply(
        lambda r: lookup.get((r["crn"], r["term_code"])), axis=1
    )

    missing = df["section_id"].isna().sum()
    if missing:
        log.warning(f"  {missing:,} rows could not be matched to a section_id and will be dropped")
        df = df.dropna(subset=["section_id"])

    return df


# ── Supabase upsert ───────────────────────────────────────────────────────────
def upsert(client: Client, table: str, df: pd.DataFrame, conflict_cols: list[str]):
    """Upsert a DataFrame into a Supabase table in batches."""
    if df.empty:
        log.info(f"  (skipping {table} — empty dataframe)")
        return

    # Replace NaN/NaT/float('nan') with None so JSON serialisation works
    # .where() misses some edge cases so we do a second pass with a list comprehension
    df = df.where(pd.notnull(df), other=None)
    records = [
        {k: (None if (v is not None and isinstance(v, float) and v != v) else v)
         for k, v in row.items()}
        for row in df.to_dict(orient="records")
    ]

    BATCH = 500
    total = len(records)
    for i in range(0, total, BATCH):
        batch = records[i : i + BATCH]
        client.table(table).upsert(batch, on_conflict=",".join(conflict_cols)).execute()
        log.info(f"  ↑  {table}  {i + len(batch):,}/{total:,} rows")

    log.info(f"  ✓  {table} done")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="PantherGrades ETL pipeline")
    parser.add_argument("--distribution", required=True, help="Path to distribution CSV folder")
    parser.add_argument("--granular",     required=True, help="Path to granular CSV folder")
    parser.add_argument("--dry-run", action="store_true", help="Parse and clean only, skip Supabase upload")
    args = parser.parse_args()

    dist_folder = Path(args.distribution)
    gran_folder = Path(args.granular)

    # ── 1. Read all files ─────────────────────────────────────────────────────
    log.info("Reading distribution CSVs...")
    dist = load_folder(dist_folder, read_distribution)
    log.info(f"  Total distribution rows: {len(dist):,}")

    log.info("Reading granular CSVs...")
    gran = load_folder(gran_folder, read_granular)
    log.info(f"  Total granular rows: {len(gran):,}")

    if dist.empty:
        log.error("No distribution data loaded. Check your folder path.")
        sys.exit(1)

    # ── 2. Build normalised tables ────────────────────────────────────────────
    log.info("Building normalised tables...")
    courses       = build_courses(dist)
    professors    = build_professors(dist)
    sections      = build_sections(dist)
    letter_totals = build_grade_letter_totals(dist)
    granular      = build_grade_granular(gran) if not gran.empty else pd.DataFrame()

    log.info(f"  courses:            {len(courses):,} unique")
    log.info(f"  professors:         {len(professors):,} unique")
    log.info(f"  sections:           {len(sections):,}")
    log.info(f"  grade_letter_totals:{len(letter_totals):,}")
    log.info(f"  grade_granular:     {len(granular):,}")

    if args.dry_run:
        log.info("Dry run complete — no data written to Supabase.")
        # Print a sample of each table
        for name, df in [("courses", courses), ("professors", professors),
                         ("sections", sections), ("letter_totals", letter_totals)]:
            print(f"\n=== {name} (first 3 rows) ===")
            print(df.head(3).to_string())
        return

    # ── 3. Connect to Supabase ────────────────────────────────────────────────
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")  # use service key for upserts
    if not url or not key:
        log.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        sys.exit(1)

    client = create_client(url, key)
    log.info("Connected to Supabase.")

    # # ── 4. Upsert in dependency order ─────────────────────────────────────────
    # # courses and professors first (referenced by sections)
    # log.info("Upserting courses...")
    # upsert(client, "courses",             courses,       ["course_code"])

    # log.info("Upserting professors...")
    # upsert(client, "professors",          professors,    ["name"])

    # log.info("Upserting sections...")
    # upsert(client, "sections", sections, ["crn", "term_code"])

    # # ── Resolve section_id FK before upserting grade tables ───────────────────
    # log.info("Resolving section IDs for grade tables...")
    # letter_totals = attach_section_ids(client, letter_totals)

    # log.info("Upserting grade_letter_totals...")
    # upsert(client, "grade_letter_totals", letter_totals, ["section_id"])

    if not granular.empty:
        log.info("Resolving section IDs for granular table...")
        granular = attach_section_ids(client, granular)
        log.info("Upserting grade_granular...")
        upsert(client, "grade_granular", granular, ["section_id"])

    log.info("ETL complete ✓")


if __name__ == "__main__":
    main()