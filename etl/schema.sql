-- PantherGrades — Supabase schema
-- Run this in the Supabase SQL editor before running the ETL pipeline.
-- Tables are created in dependency order.

-- ── Extensions ────────────────────────────────────────────────────────────────
create extension if not exists "uuid-ossp";

-- ── courses ───────────────────────────────────────────────────────────────────
create table if not exists courses (
  id             uuid primary key default uuid_generate_v4(),
  course_code    text not null unique,   -- e.g. "ACCT 2102"
  department     text,                   -- e.g. "ACCT"
  course_number  text,                   -- e.g. "2102"
  created_at     timestamptz default now()
);

create index if not exists idx_courses_department on courses (department);

-- ── professors ────────────────────────────────────────────────────────────────
create table if not exists professors (
  id           uuid primary key default uuid_generate_v4(),
  name         text not null unique,   -- "Last, First" as it appears in data
  department   text,
  name_visible boolean not null default false,  -- paywall flag
  created_at   timestamptz default now()
);

create index if not exists idx_professors_department on professors (department);
create index if not exists idx_professors_name_visible on professors (name_visible);

-- ── sections ──────────────────────────────────────────────────────────────────
create table if not exists sections (
  id                uuid primary key default uuid_generate_v4(),
  crn               text not null,
  term_code         text not null,          -- e.g. "200508" (YYYYMM)
  course_code       text references courses (course_code),
  professor_name    text references professors (name),
  semester          text,                   -- "Fall" | "Spring" | "Summer"
  year              int,
  total             int,
  other             int,                    -- auditors / incompletes / no grade
  has_grades        boolean,
  instruction_method text,                  -- in_person | online | hybrid | ...
  created_at        timestamptz default now(),
  unique (crn, term_code)
);

create index if not exists idx_sections_course      on sections (course_code);
create index if not exists idx_sections_professor   on sections (professor_name);
create index if not exists idx_sections_term        on sections (term_code);
create index if not exists idx_sections_year        on sections (year);

-- ── grade_letter_totals ───────────────────────────────────────────────────────
-- Broad A/B/C/D/F buckets — from the distribution CSVs
create table if not exists grade_letter_totals (
  id          uuid primary key default uuid_generate_v4(),
  crn         text not null,
  term_code   text not null,
  grade_a     int,
  grade_b     int,
  grade_c     int,
  grade_d     int,
  grade_f     int,
  wf          int,    -- Withdraw-Fail
  w           int,    -- Withdraw (passing)
  other       int,
  gpa_avg     numeric(4, 2),   -- GSU allows up to 4.33 for A+
  dwf_pct     numeric(5, 2),   -- % of students with D, WF, or F
  a_minus_wf  int,             -- students with A- or better who withdrew/failed
  created_at  timestamptz default now(),
  unique (crn, term_code)
);

create index if not exists idx_glt_crn_term on grade_letter_totals (crn, term_code);

-- ── grade_granular ────────────────────────────────────────────────────────────
-- Plus/minus breakdown — from the granular CSVs
create table if not exists grade_granular (
  id          uuid primary key default uuid_generate_v4(),
  crn         text not null,
  term_code   text not null,
  a_plus      int,
  a           int,
  a_minus     int,
  b_plus      int,
  b           int,
  b_minus     int,
  c_plus      int,
  c           int,
  c_minus     int,
  d           int,
  f           int,
  wf          int,
  w           int,
  other       int,
  dwf_pct     numeric(5, 2),
  a_minus_wf  int,
  created_at  timestamptz default now(),
  unique (crn, term_code)
);

create index if not exists idx_gg_crn_term on grade_granular (crn, term_code);

-- ── users ─────────────────────────────────────────────────────────────────────
-- Managed by Supabase Auth; this table extends auth.users
create table if not exists user_profiles (
  id                 uuid primary key references auth.users (id) on delete cascade,
  tier               text not null default 'free',   -- 'free' | 'pro'
  stripe_customer_id text unique,
  subscribed_at      timestamptz,
  created_at         timestamptz default now()
);

-- ── Row-level security ────────────────────────────────────────────────────────
-- Enable RLS on user_profiles so users can only read their own row
alter table user_profiles enable row level security;

create policy "Users can view own profile"
  on user_profiles for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on user_profiles for update
  using (auth.uid() = id);

-- Grade and course tables are public read
alter table courses             enable row level security;
alter table professors          enable row level security;
alter table sections            enable row level security;
alter table grade_letter_totals enable row level security;
alter table grade_granular      enable row level security;

create policy "Public read courses"             on courses             for select using (true);
create policy "Public read sections"            on sections            for select using (true);
create policy "Public read grade_letter_totals" on grade_letter_totals for select using (true);
create policy "Public read grade_granular"      on grade_granular      for select using (true);

-- Professors: name only visible if name_visible = true OR user is pro
create policy "Professor visibility"
  on professors for select
  using (
    name_visible = true
    or exists (
      select 1 from user_profiles
      where id = auth.uid() and tier = 'pro'
    )
  );
