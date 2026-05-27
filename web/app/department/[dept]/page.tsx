import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";

interface Props {
  params: Promise<{ dept: string }>;
  searchParams: Promise<{ terms?: string }>;
}

export default async function DepartmentPage({ params, searchParams }: Props) {
  const { dept: rawDept } = await params;
  const { terms: termsParam } = await searchParams;
  const dept = rawDept.toUpperCase();
  const termCount = Math.min(Math.max(parseInt(termsParam ?? "10"), 1), 20);

  let schedule;
  try {
    schedule = await api.getDepartmentSchedule(dept, termCount);
  } catch {
    notFound();
  }

  const { term_codes, term_labels, rows } = schedule;

  return (
    <main className="min-h-screen bg-slate-50">
      {/* Nav */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between flex-wrap gap-3">
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
            <span className="text-sm text-slate-400">Department</span>
          </div>

          {/* Term count switcher */}
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <span className="text-xs">Semesters:</span>
            {[4, 6, 10].map((n) => (
              <Link
                key={n}
                href={`/department/${dept}?terms=${n}`}
                className={`px-3 py-1 rounded-lg transition-colors text-xs font-medium ${
                  termCount === n
                    ? "bg-blue-600 text-white"
                    : "bg-white border border-slate-200 hover:bg-slate-50 text-slate-600"
                }`}
              >
                {n}
              </Link>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-extrabold text-slate-900">
            {dept} Course Schedule
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            {rows.length} courses · last {termCount} semesters ·{" "}
            <span className="italic">instructor names are anonymized</span>
          </p>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400 sticky left-0 bg-slate-50 z-10 min-w-56 border-r border-slate-200">
                    Course
                  </th>
                  {term_codes.map((tc) => (
                    <th
                      key={tc}
                      className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-slate-400 min-w-32 whitespace-nowrap"
                    >
                      {term_labels[tc]}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((row) => (
                  <tr key={row.course_code} className="hover:bg-slate-50 transition-colors">
                    {/* Course name cell */}
                    <td className="px-5 py-4 align-top sticky left-0 bg-white border-r border-slate-100 z-10">
                      <Link
                        href={`/course/${encodeURIComponent(row.course_code)}`}
                        className="group block"
                      >
                        <span className="font-mono text-sm font-semibold text-blue-600 group-hover:underline">
                          {row.course_code}
                        </span>
                        {row.title && (
                          <p className="text-xs text-slate-500 mt-0.5 leading-snug max-w-[200px]">
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
                          <td key={tc} className="px-4 py-4 text-center align-middle">
                            <span className="text-xs text-slate-300 italic">Not offered</span>
                          </td>
                        );
                      }
                      return (
                        <td key={tc} className="px-4 py-4 align-top">
                          <div className="flex flex-col gap-1">
                            {cell.instructors.length > 0 ? (
                              cell.instructors.map((label) => (
                                <span
                                  key={label}
                                  className="text-xs text-slate-700 bg-slate-100 px-2 py-0.5 rounded-md inline-block whitespace-nowrap"
                                >
                                  {label}
                                </span>
                              ))
                            ) : (
                              <span className="text-xs text-slate-400 italic">Unknown</span>
                            )}
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

        <p className="text-xs text-slate-400 text-center mt-6 max-w-2xl mx-auto">
          Instructor labels are anonymized — the same label always refers to the same instructor within this table, but labels are not consistent across departments or page loads.
          GPA shown is the average across all sections in that semester.
        </p>
      </div>
    </main>
  );
}