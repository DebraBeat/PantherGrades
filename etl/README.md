# PantherGrades ETL Pipeline

Loads GSU grade distribution CSVs into Supabase.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your Supabase credentials
```

**.env**
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
```

Use the **service role key** (not the anon key) — the ETL needs to bypass RLS to write data.

## Folder structure

```
data/
  distribution/
    distribution_fa_05.csv
    distribution_sp_06.csv
    ...
  granular/
    granular_fa_05.csv
    granular_sp_06.csv
    ...
```

## Run

**Dry run first (no writes to Supabase):**
```bash
python pipeline.py \
  --distribution ./data/distribution \
  --granular ./data/granular \
  --dry-run
```

**Full load:**
```bash
python pipeline.py \
  --distribution ./data/distribution \
  --granular ./data/granular
```

## First time setup

1. Run `schema.sql` in the Supabase SQL editor
2. Run the pipeline with `--dry-run` to verify parsing
3. Run the full pipeline to load all historical data
4. Re-run each semester when new data is released — upserts are safe to re-run

## Supported semester codes

| Code | Semester | Term month |
|------|----------|------------|
| fa   | Fall     | 08         |
| sp   | Spring   | 01         |
| su   | Summer   | 05         |

## Notes

- GPA values above 4.0 are valid — GSU awards A+ as 4.33
- Sections where all students are in the `other` column (auditors, incompletes) are flagged as `has_grades = false` and excluded from GPA calculations
- The `professors.name_visible` column defaults to `false` — the paywall flag. Flip it to `true` manually or via an admin script when a user subscribes
