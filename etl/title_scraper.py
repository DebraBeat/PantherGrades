"""
GSU Course Catalog Scraper
==========================
Scrapes course titles from the GSU Acalog catalog across pages 1-37
and upserts them into the courses.title column in Supabase.

Usage:
    pip install requests beautifulsoup4 supabase python-dotenv
    python scrape_titles.py --dry-run     # parse only, no DB writes
    python scrape_titles.py               # full run
"""

import argparse
import logging
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("scraper")

# ── Config ─────────────────────────────────────────────────────────────────────

BASE_URL = (
    "https://catalogs.gsu.edu/content.php"
    "?catoid=42&navoid=5314"
    "&filter[27]=-1&filter[29]=&filter[course_type]=-1"
    "&filter[keyword]=&filter[32]=1"
    "&filter[cpage]={page}"
    "&filter[exact_match]=1&filter[item_type]=3"
    "&filter[only_active]=1&filter[3]=1&print"
)

TOTAL_PAGES = 37
DELAY = 1.0  # seconds between requests — be polite to the server

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PantherGrades-scraper/1.0; "
        "educational use)"
    )
}


# ── Parser ─────────────────────────────────────────────────────────────────────

def parse_page(html: str) -> list[dict]:
    """
    Parse a single catalog page and return a list of
    {"course_code": "ACCT 2102", "title": "Principles of Accounting II"}
    
    Acalog renders courses as links like:
      ACCT 2102 - Principles of Accounting II
    inside <td> elements within the course filter table.
    """
    soup = BeautifulSoup(html, "html.parser")
    courses = []

    # Acalog puts course rows in a table with class "table_default"
    # Each row has a link whose text is "PREFIX NNNN - Title"
    for link in soup.select("td.width a"):
        text = link.get_text(separator=" ", strip=True)

        # Match patterns like:
        #   ACCT 2102 - Principles of Accounting II
        #   CS 2340 - Objects and Design
        match = re.match(
            r"^([A-Z]{2,6})\s+(\w+)\s*[-–]\s*(.+)$", text
        )
        if not match:
            continue

        dept     = match.group(1).strip()
        number   = match.group(2).strip()
        title    = match.group(3).strip()
        code     = f"{dept} {number}"

        courses.append({"course_code": code, "title": title})

    return courses


# ── Scrape ─────────────────────────────────────────────────────────────────────

def scrape_all(start: int = 1, end: int = TOTAL_PAGES) -> list[dict]:
    all_courses: list[dict] = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for page in range(start, end + 1):
        url = BASE_URL.format(page=page)
        log.info(f"Fetching page {page}/{end} ...")

        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            log.warning(f"  Page {page} failed: {e} — skipping")
            time.sleep(DELAY)
            continue

        courses = parse_page(resp.text)
        log.info(f"  Found {len(courses)} courses on page {page}")
        all_courses.extend(courses)

        time.sleep(DELAY)

    # Deduplicate by course_code (keep last occurrence)
    seen: dict[str, dict] = {}
    for c in all_courses:
        seen[c["course_code"]] = c

    result = list(seen.values())
    log.info(f"Total unique courses scraped: {len(result)}")
    return result


# ── Supabase upsert ────────────────────────────────────────────────────────────

def upsert_titles(courses: list[dict]):
    from supabase import create_client

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    client = create_client(url, key)

    BATCH = 500
    total = len(courses)
    for i in range(0, total, BATCH):
        batch = courses[i : i + BATCH]
        # Only update the title column; leave everything else untouched
        client.table("courses").upsert(
            batch, on_conflict="course_code"
        ).execute()
        log.info(f"  Upserted {i + len(batch):,}/{total:,} titles")

    log.info("Done ✓")


# ── Debug: print first 20 results ──────────────────────────────────────────────

def preview(courses: list[dict], n: int = 20):
    print(f"\n{'Course Code':<15} {'Title'}")
    print("-" * 60)
    for c in courses[:n]:
        print(f"{c['course_code']:<15} {c['title']}")
    print(f"\n... {len(courses)} total courses scraped")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Scrape GSU course titles")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scrape and print only, skip Supabase upsert")
    parser.add_argument("--start", type=int, default=1,
                        help="Start page (default: 1)")
    parser.add_argument("--end", type=int, default=TOTAL_PAGES,
                        help=f"End page (default: {TOTAL_PAGES})")
    parser.add_argument("--page", type=int, default=None,
                        help="Scrape a single page for testing")
    args = parser.parse_args()

    if args.page:
        args.start = args.page
        args.end = args.page

    courses = scrape_all(start=args.start, end=args.end)
    preview(courses)

    if args.dry_run:
        log.info("Dry run — skipping Supabase upsert")
        return

    upsert_titles(courses)


if __name__ == "__main__":
    main()