const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Course {
  id: string;
  course_code: string;
  department: string | null;
  course_number: string | null;
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

export const api = {
  searchCourses: (q: string) =>
    apiFetch<Course[]>(`/courses/search?q=${encodeURIComponent(q)}&limit=10`),

  getCourse: (code: string) =>
    apiFetch<CourseDetail>(`/courses/${encodeURIComponent(code)}`),

  getCourseSummary: (code: string) =>
    apiFetch<CourseSummary>(`/analytics/course/${encodeURIComponent(code)}/summary`),

  getCourseTrend: (code: string) =>
    apiFetch<TrendPoint[]>(`/analytics/course/${encodeURIComponent(code)}/trend`),

  getSections: (code: string) =>
    apiFetch<Section[]>(`/sections/by-course/${encodeURIComponent(code)}`),
};