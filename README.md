# PantherGrades

**Know what to expect before you enroll.**

PantherGrades is a data-driven course planning tool for Georgia State University students. It surfaces real grade distribution data for every GSU course going back to Fall 2005 — so students can make smarter decisions at registration.

🔗 **[panther-grades.vercel.app](https://panther-grades.vercel.app)**
📊 **[Grade inflation analysis](https://019e620b-069d-6d1e-02a3-f35f60e198a9.share.connect.posit.cloud/)** — statistical analysis of grade inflation at GSU
🎥 **[![Watch the video](https://img.youtube.com/vi/GD6SgRUoRzo/hqdefault.jpg)](https://www.youtube.com/embed/GD6SgRUoRzo)**
---

## Features

- **Course search** by course code, title, or department — e.g. `BIOL 1103`, `Calculus`, `ACCT`
- **Grade distributions** — A/B/C/D/F/W breakdown for every course section since 2005
- **Predicted grade distribution** — exponentially-weighted model that gives more weight to recent semesters
- **Semester GPA trend** — track whether a course is getting harder or easier over time
- **Department schedule** — see every course in a department with instructors by semester
- **Department context** — every stat shown against the department average

---

## Screenshots

> *(add screenshots here)*

---

## Architecture

```
┌─────────────────┐      ┌──────────────────┐     ┌─────────────────┐       ┌─────────────────┐
│   iPort GSU     │      │   ETL Pipeline   │     │    Supabase     │       | Grade Inflation |
│   Grade        │────▶ │   (Python /      │────▶│   PostgreSQL    │────▶ | Analysis        |
│   Distribition  │      │    pandas)       │     │                 │       |                 |
|   Portal        |      └──────────────────┘     └────────┬────────┘       | Course          |
└─────────────────┘                                        │                | Difficulty      |
                        ┌──────────────────┐               │                | Analysis        |
                        │  FastAPI (Python) │◀─────────────┘               └──────────────────┘ 
                        │  Railway         │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │  Next.js / React  │
                        │  Vercel Frontend  │
                        └──────────────────┘
```

**Stack:**
- **Frontend:** Next.js 16, React, Tailwind CSS, Recharts, shadcn/ui — deployed on Vercel
- **Backend:** FastAPI (Python) — deployed on Railway
- **Database:** Supabase (PostgreSQL) with row-level security
- **ETL:** Python, pandas — run locally and on-demand each semester
- **Analysis:** R, tidyverse, ggplot2, RPostgres

---

## Data

All grade data comes from GSU's [public grade distribution portal](https://dssapex.gsu.edu/ords/f?p=140:1::::NO).

| Stat | Value |
|------|-------|
| Semesters covered | Fall 2005 – Spring 2026 |
| Course sections | 262,000+ |
| Unique courses | 2,200+ |
| Unique instructors | 2,400+ |

Data is aggregate only — no individual student records are used or stored.

---

## Prediction Model

Each course page includes a predicted grade distribution computed by a recency-weighted model:

1. **Recency weighting** — each historical section is weighted using exponential decay with a half-life of 6 semesters (2 years), so recent semesters count more than old ones: `weight = 2^(-(age / 6))`
2. **Size weighting** — larger sections carry more weight: `final_weight = recency_weight × enrollment`
3. **Normalization** — predicted probabilities are normalized to sum to 1.0
4. **Confidence** — rated high/medium/low based on effective sample size (ESS)
5. **Instruction method split** — separate predictions for in-person vs online sections where data allows

Predictions are pre-computed and stored in Supabase, regenerated each semester.

**References:**
- Hyndman & Athanasopoulos, *Forecasting: Principles and Practice* (exponential smoothing) — [otexts.com/fpp3](https://otexts.com/fpp3)

---

## Grade Inflation Analysis

A full statistical analysis of grade inflation at GSU is available here:
**[Analysis of Grade Inflation at Georgia State University](https://019e620b-069d-6d1e-02a3-f35f60e198a9.share.connect.posit.cloud/)**

Key findings:
- A statistically significant structural break in grade distributions coinciding with COVID-19 (2020)
- A further shift in the Post-AI period (2023–2025) consistent with national trends
- Both the proportion of A grades and average GPA show significant upward trends across all three periods
- DWF rates declined during COVID and have partially recovered

Analysis conducted in R using tidyverse, with statistical tests of proportions, linear regression slope comparisons across periods, and a forecast to 2028.

---

## Project Structure

```
PantherGrades/
├── etl/
│   ├── pipeline.py          # Ingests CSVs → Supabase
│   ├── scrape_titles.py     # Scrapes course titles from GSU catalog
│   ├── predict.py           # Prediction model — generates course_predictions table
│   └── schema.sql           # Supabase schema migrations
│
├── api/
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── auth.py
│       └── routers/
│           ├── courses.py
│           ├── sections.py
│           ├── analytics.py
│           └── department.py
│
├── web/
│   ├── app/
│   │   ├── page.tsx               # Home page
│   │   ├── about/page.tsx         # About + methodology
│   │   ├── course/[code]/page.tsx # Course detail
│   │   └── department/[dept]/page.tsx
│   ├── components/
│   │   ├── SearchBar.tsx
│   │   ├── GradeChart.tsx
│   │   ├── TrendChart.tsx
│   │   ├── PredictionChart.tsx
│   │   ├── StatCard.tsx
│   │   └── DataSourceBanner.tsx
│   └── lib/
│       └── api.ts
│
└── analysis/
    └── grade_inflation.qmd    # R/Quarto grade inflation analysis
```

---

## Running Locally

**API:**
```bash
cd api
uv venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env   # add Supabase credentials
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd web
npm install
cp .env.local.example .env.local   # add NEXT_PUBLIC_API_URL
npm run dev
```

**ETL (re-run each semester):**
```bash
cd etl
source ../.venv/bin/activate
python3 pipeline.py --distribution ./data/distribution --granular ./data/granular
python3 scrape_titles.py
python3 predict.py
```

---

## Disclaimer

PantherGrades is an independent student resource and is not affiliated with or endorsed by Georgia State University. All data is sourced from publicly available GSU records. Grade distributions reflect many factors — use alongside your advisor's guidance when making enrollment decisions.
