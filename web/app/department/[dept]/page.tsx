import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ScheduleCell {
  term_code: string;
  semester: string;
  year: number;
  instructors: string[];
  avg_gpa: number | null;
  total_students: number | null;
}

interface ScheduleRow {
  course_code: string;
  title: string | null;
  course_number: string | null;
  terms: Record<string, ScheduleCell>;
}

interface DepartmentSchedule {
  department: string;
  term_codes: string[];
  term_labels: Record<string, string>;
  rows: ScheduleRow[];
}

interface Props {
  params: Promise<{ dept: string }>;
  searchParams: Promise<{ terms?: string }>;
}

async function getSchedule(dept: string, terms: number): Promise<DepartmentSchedule> {
  const res = await fetch(
    `${API_URL}/department/${encodeURIComponent(dept)}/schedule?terms=${terms}`,
    { next: { revalidate: 3600 } }
  );
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export default async function DepartmentPage({ params, searchParams }: Props) {
  const { dept: rawDept } = await params;
  const { terms: termsParam } = await searchParams;
  const dept = rawDept.toUpperCase();
  const termCount = Math.min(Math.max(parseInt(termsParam ?? "4"), 1), 12);

  let schedule: DepartmentSchedule;
  try {
    schedule = await getSchedule(dept, termCount);
  } catch {
    notFound();
  }

  const { term_codes, term_labels, rows } = schedule;

  return (
    <main className="min-h-screen bg-slate-50">
      {/* Nav */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </Link>
            <span className="text-slate-300">|</span>
            <span className="font-bold text-slate-800 text-lg">{dept}</span>
            <span className="text-sm text-slate-400">Department Schedule</span>
          </div>

          {/* Term count selector */}
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <span>Show:</span>
            {[2, 4, 6, 8].map((n) => (
              <Link
                key={n}
                href={`/department/${dept}?terms=${n}`}
                className={`px-3 py-1 rounded-lg transition-colors ${
                  termCount === n
                    ? "bg-blue-600 text-white font-semibold"
                    : "bg-white border border-slate-200 hover:bg-slate-50"
                }`}
              >
                {n} terms
              </Link>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-extrabold text-slate-900">
            {dept} Course Schedule
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            {rows.length} courses · last {termCount} semesters · instructor labels are anonymized
          </p>
        </div>

        {/* Table */}
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400 w-48 min-w-48">
                    Course
                  </th>
                  {term_codes.map((tc) => (
                    <th
                      key={tc}
                      className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-slate-400 min-w-36"
                    >
                      {term_labels[tc]}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((row) => (
                  <tr key={row.course_code} className="hover:bg-slate-50 transition-colors">
                    {/* Course cell */}
                    <td className="px-5 py-4 align-top">
                      <Link
                        href={`/course/${encodeURIComponent(row.course_code)}`}
                        className="group"
                      >
                        <span className="font-mono text-sm font-semibold text-blue-600 group-hover:underline">
                          {row.course_code}
                        </span>
                        {row.title && (
                          <p className="text-xs text-slate-500 mt-0.5 leading-snug max-w-[180px]">
                            {row.title}
                          </p>
                        )}
                      </Link>
                    </td>

                    {/* Term cells */}
                    {term_codes.map((tc) => {
                      const cell = row.terms[tc];
                      if (!cell) {
                        return (
                          <td key={tc} className="px-4 py-4 text-center text-slate-200">
                            —
                          </td>
                        );
                      }
                      return (
                        <td key={tc} className="px-4 py-4 align-top">
                          <div className="flex flex-col gap-1">
                            {cell.instructors.map((label) => (
                              <span
                                key={label}
                                className="text-xs text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md inline-block"
                              >
                                {label}
                              </span>
                            ))}
                            {cell.avg_gpa != null && (
                              <span className="text-xs text-slate-400 mt-0.5">
                                GPA {cell.avg_gpa.toFixed(2)}
                              </span>
                            )}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Disclaimer */}
        <p className="text-xs text-slate-400 text-center mt-6">
          Instructor labels are anonymized. Same label = same instructor within this table.
          GPA shown is the average across all sections that semester.
        </p>
      </div>
    </main>
  );
}