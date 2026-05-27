const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Course {
  id: string;
  course_code: string;
  department: string | null;
  course_number: string | null;
  title: string | null;
}

export interface CourseDetail extends Course {
  total_sections: number;
  avg_gpa: number | null;
  avg_dwf_pct: number | null;
}

export interface GradeLetterTotals {
  grade_a: number | null;
  grade_b: number | null;
  grade_c: number | null;
  grade_d: number | null;
  grade_f: number | null;
  wf: number | null;
  w: number | null;
  gpa_avg: number | null;
  dwf_pct: number | null;
}

export interface ProfessorInfo {
  label: string;
  is_anonymous: boolean;
  department: string | null;
}

export interface Section {
  id: string;
  crn: string;
  term_code: string;
  semester: string | null;
  year: number | null;
  course_code: string | null;
  total: number | null;
  instruction_method: string | null;
  has_grades: boolean | null;
  professor: ProfessorInfo | null;
  grade_letter_totals: GradeLetterTotals | null;
}

export interface CourseSummary {
  course_code: string;
  department: string;
  total_sections: number;
  total_students: number;
  avg_gpa: number | null;
  dept_avg_gpa: number | null;
  gpa_vs_dept: number | null;
  avg_dwf_pct: number | null;
  dept_avg_dwf_pct: number | null;
  pct_online: number | null;
  pct_in_person: number | null;
  pct_other: number | null;
}

export interface TrendPoint {
  semester: string;
  year: number;
  term_code: string;
  avg_gpa: number | null;
  avg_dwf_pct: number | null;
  total_students: number;
  section_count: number;
}

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { next: { revalidate: 3600 } });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

export interface GradePrediction {
  instruction_method: string;
  pred_a: number | null;
  pred_b: number | null;
  pred_c: number | null;
  pred_d: number | null;
  pred_f: number | null;
  pred_w: number | null;
  pred_gpa: number | null;
  n_sections: number | null;
  n_students: number | null;
  confidence: string | null;
  latest_term: string | null;
}

export interface DepartmentSummary {
  department: string;
  course_count: number;
}

export interface ScheduleCell {
  instructors: string[];
  avg_gpa: number | null;
}

export interface ScheduleRow {
  course_code: string;
  title: string | null;
  terms: Record<string, ScheduleCell | null>;
}

export interface DepartmentSchedule {
  department: string;
  term_codes: string[];
  term_labels: Record<string, string>;
  rows: ScheduleRow[];
}

export const api = {
  searchCourses: (q: string) =>
    apiFetch<Course[]>(`/courses/search?q=${encodeURIComponent(q)}&limit=10`),

  getDepartments: () =>
    apiFetch<string[]>(`/courses/departments`),

  listDepartments: () =>
    apiFetch<DepartmentSummary[]>(`/department`),

  getCoursePrediction: (code: string) =>
    apiFetch<GradePrediction[]>(`/analytics/course/${encodeURIComponent(code)}/prediction`),

  getDepartmentSchedule: (dept: string, terms = 10) =>
    apiFetch<DepartmentSchedule>(`/department/${encodeURIComponent(dept)}/schedule?terms=${terms}`),

  getCourse: (code: string) =>
    apiFetch<CourseDetail>(`/courses/${encodeURIComponent(code)}`),

  getCourseSummary: (code: string) =>
    apiFetch<CourseSummary>(`/analytics/course/${encodeURIComponent(code)}/summary`),

  getCourseTrend: (code: string) =>
    apiFetch<TrendPoint[]>(`/analytics/course/${encodeURIComponent(code)}/trend`),

  getSections: (code: string) =>
    apiFetch<Section[]>(`/sections/by-course/${encodeURIComponent(code)}`),
};