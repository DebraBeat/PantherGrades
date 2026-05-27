import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Users, BookOpen, Wifi, Building2 } from "lucide-react";
import { api, Section } from "@/lib/api";
import StatCard from "@/components/StatCard";
import DataSourceBanner from "@/components/DataSourceBanner";
import PredictionChart from "@/components/PredictionChart";
import GradeChart from "@/components/GradeChart";
import TrendChart from "@/components/TrendChart";

interface Props {
  params: Promise<{ code: string }>;
}

// Aggregate grade totals across all sections for the chart
function aggregateTotals(sections: Section[]) {
  const totals = {
    grade_a: 0, grade_b: 0, grade_c: 0,
    grade_d: 0, grade_f: 0, wf: 0, w: 0,
    gpa_avg: null as number | null,
    dwf_pct: null as number | null,
  };
  let totalStudents = 0;
  const gpas: number[] = [];
  const dwfs: number[] = [];

  for (const s of sections) {
    const g = s.grade_letter_totals;
    if (!g || !s.has_grades) continue;
    totals.grade_a += g.grade_a ?? 0;
    totals.grade_b += g.grade_b ?? 0;
    totals.grade_c += g.grade_c ?? 0;
    totals.grade_d += g.grade_d ?? 0;
    totals.grade_f += g.grade_f ?? 0;
    totals.wf      += g.wf ?? 0;
    totals.w       += g.w ?? 0;
    totalStudents  += s.total ?? 0;
    if (g.gpa_avg  != null) gpas.push(g.gpa_avg);
    if (g.dwf_pct  != null) dwfs.push(g.dwf_pct);
  }

  totals.gpa_avg  = gpas.length  ? gpas.reduce((a, b) => a + b) / gpas.length   : null;
  totals.dwf_pct  = dwfs.length  ? dwfs.reduce((a, b) => a + b) / dwfs.length   : null;
  return { totals, totalStudents };
}

export default async function CoursePage({ params }: Props) {
  const { code: rawCode } = await params;
  const code = decodeURIComponent(rawCode).toUpperCase();

  const [summary, trend, sections, courseDetail, prediction] = await Promise.allSettled([
    api.getCourseSummary(code),
    api.getCourseTrend(code),
    api.getSections(code),
    api.getCourse(code),
    api.getCoursePrediction(code),
  ]);

  if (summary.status === "rejected") notFound();

  const s           = summary.value;
  const trendData   = trend.status        === "fulfilled" ? trend.value        : [];
  const sectionData = sections.status     === "fulfilled" ? sections.value     : [];
  const title       = courseDetail.status === "fulfilled" ? courseDetail.value.title : null;
  const predictions = prediction.status === "fulfilled" ? prediction.value : null;

  const { totals, totalStudents } = aggregateTotals(sectionData);

  const gpaVsDept = s.gpa_vs_dept;
  const gpaHighlight =
    gpaVsDept == null ? "neutral" : gpaVsDept >= 0 ? "good" : "bad";
  const gpaVsDeptStr =
    gpaVsDept == null
      ? undefined
      : `${gpaVsDept >= 0 ? "+" : ""}${gpaVsDept.toFixed(2)} vs dept avg (${s.dept_avg_gpa?.toFixed(2)})`;

  const dwfHighlight =
    s.avg_dwf_pct == null || s.dept_avg_dwf_pct == null
      ? "neutral"
      : s.avg_dwf_pct <= s.dept_avg_dwf_pct
      ? "good"
      : "bad";

  return (
    <main className="min-h-screen bg-slate-50">
      {/* Nav */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-4">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Link>
          <span className="text-slate-300">|</span>
          <span className="font-mono font-bold text-slate-800">{code}</span>
          {title && <span className="text-sm text-slate-400 truncate max-w-xs">{title}</span>}
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-10 flex flex-col gap-8">

        {/* Header */}
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
              {code}
            </h1>
            <span className="text-sm font-medium text-blue-600 bg-blue-50 px-2.5 py-1 rounded-lg">
              {s.department}
            </span>
          </div>
          {title && (
            <p className="text-lg text-slate-600 mt-1 font-medium">{title}</p>
          )}
          <p className="text-slate-400 text-sm mt-1">
            {s.total_sections} sections &middot; {s.total_students.toLocaleString()} total students
          </p>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="Avg GPA"
            value={s.avg_gpa?.toFixed(2) ?? "—"}
            sub={gpaVsDeptStr}
            highlight={gpaHighlight}
          />
          <StatCard
            label="DWF rate"
            value={s.avg_dwf_pct != null ? `${s.avg_dwf_pct.toFixed(1)}%` : "—"}
            sub={`Dept avg: ${s.dept_avg_dwf_pct?.toFixed(1) ?? "—"}%`}
            highlight={dwfHighlight}
          />
          <StatCard
            label="Online"
            value={s.pct_online != null ? `${s.pct_online.toFixed(0)}%` : "—"}
            sub="of sections"
          />
          <StatCard
            label="In person"
            value={s.pct_in_person != null ? `${s.pct_in_person.toFixed(0)}%` : "—"}
            sub="of sections"
          />
        </div>

        {/* Grade distribution */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col gap-4">
          <div>
            <h2 className="font-semibold text-slate-800">Grade distribution</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Aggregated across all {s.total_sections} sections · {totalStudents.toLocaleString()} students
            </p>
          </div>
          <GradeChart totals={totals} totalStudents={totalStudents} />
        </div>

        {/* Grade prediction */}
        {predictions && predictions.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col gap-4">
            <div>
              <h2 className="font-semibold text-slate-800">Expected grade distribution</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Predicted based on historical data · weighted toward recent semesters
              </p>
            </div>
            <PredictionChart predictions={predictions} />
          </div>
        )}

        {/* GPA trend */}
        {trendData.length > 1 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col gap-4">
            <div>
              <h2 className="font-semibold text-slate-800">GPA trend over time</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Average GPA per semester · dashed line = department average
              </p>
            </div>
            <TrendChart data={trendData} deptAvgGpa={s.dept_avg_gpa} />
          </div>
        )}

        {/* Recent sections table */}
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100">
            <h2 className="font-semibold text-slate-800">Recent sections</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 text-xs text-slate-400 uppercase tracking-wide">
                  <th className="px-6 py-3 text-left font-semibold">Term</th>
                  <th className="px-6 py-3 text-left font-semibold">Instructor</th>
                  <th className="px-6 py-3 text-left font-semibold">Students</th>
                  <th className="px-6 py-3 text-left font-semibold">Avg GPA</th>
                  <th className="px-6 py-3 text-left font-semibold">DWF %</th>
                  <th className="px-6 py-3 text-left font-semibold">Format</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sectionData.slice(0, 20).map((section) => (
                  <tr key={section.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-3.5 font-medium text-slate-700 whitespace-nowrap">
                      {section.semester} {section.year}
                    </td>
                    <td className="px-6 py-3.5 text-slate-600">
                      {section.professor ? (
                        <span className={section.professor.is_anonymous ? "text-slate-400 italic" : ""}>
                          {section.professor.label}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-6 py-3.5 text-slate-600">
                      {section.total ?? "—"}
                    </td>
                    <td className="px-6 py-3.5 font-semibold text-slate-700">
                      {section.grade_letter_totals?.gpa_avg?.toFixed(2) ?? "—"}
                    </td>
                    <td className="px-6 py-3.5 text-slate-600">
                      {section.grade_letter_totals?.dwf_pct != null
                        ? `${section.grade_letter_totals.dwf_pct.toFixed(1)}%`
                        : "—"}
                    </td>
                    <td className="px-6 py-3.5 text-slate-500 capitalize">
                      {section.instruction_method?.replace("_", " ") ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Data source banner */}
        <DataSourceBanner />
      </div>
    </main>
  );
}