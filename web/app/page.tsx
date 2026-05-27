import Link from "next/link";
import { GraduationCap, BarChart2, TrendingUp, Shield } from "lucide-react";
import SearchBar from "@/components/SearchBar";
import { api } from "@/lib/api";

const FEATURES = [
  {
    icon: BarChart2,
    title: "Grade distributions",
    desc: "See exactly how grades break down for every course section — A through W — going back to 2005.",
  },
  {
    icon: TrendingUp,
    title: "Semester trends",
    desc: "Track how a course's average GPA has shifted over time and spot whether it's getting harder or easier.",
  },
  {
    icon: Shield,
    title: "Department context",
    desc: "Every stat is shown alongside the department average so you know if a 3.1 GPA is actually good or bad.",
  },
];

export default async function HomePage() {
  // Fetch departments server-side for the listing
  let departments: { department: string; course_count: number }[] = [];
  try {
    departments = await api.listDepartments();
  } catch {
    // fail silently — departments section just won't render
  }

  return (
    <main className="min-h-screen bg-slate-50">
      {/* Hero */}
      <section className="bg-white border-b border-slate-200">
        <div className="max-w-4xl mx-auto px-6 py-20 flex flex-col items-center text-center gap-8">
          <div className="flex items-center gap-2.5 text-blue-600 font-semibold text-sm tracking-wide uppercase">
            <GraduationCap className="w-5 h-5" />
            <span>Georgia State University</span>
          </div>

          <h1 className="text-5xl font-extrabold text-slate-900 leading-tight tracking-tight">
            Know what to expect
            <br />
            <span className="text-blue-600">before you enroll.</span>
          </h1>

          <p className="text-lg text-slate-500 max-w-xl leading-relaxed">
            PantherGrades gives you real grade distribution data for every GSU
            course — so you can make smarter decisions at registration.
          </p>

          <SearchBar />

          <p className="text-xs text-slate-400">
            Search by course code, title, or department · Data from official GSU records · 2005–2026
          </p>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-4xl mx-auto px-6 py-12 grid grid-cols-1 md:grid-cols-3 gap-6">
        {FEATURES.map(({ icon: Icon, title, desc }) => (
          <div
            key={title}
            className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col gap-3"
          >
            <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
              <Icon className="w-5 h-5 text-blue-600" />
            </div>
            <h3 className="font-semibold text-slate-800">{title}</h3>
            <p className="text-sm text-slate-500 leading-relaxed">{desc}</p>
          </div>
        ))}
      </section>

      {/* Departments */}
      {departments.length > 0 && (
        <section className="max-w-4xl mx-auto px-6 pb-16">
          <h2 className="text-xl font-bold text-slate-800 mb-4">Browse by department</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {departments.map(({ department, course_count }) => (
              <Link
                key={department}
                href={`/department/${department}`}
                className="bg-white rounded-xl border border-slate-200 px-4 py-3 flex flex-col gap-0.5 hover:border-blue-300 hover:bg-blue-50 transition-colors group"
              >
                <span className="font-mono font-bold text-slate-800 group-hover:text-blue-600 transition-colors">
                  {department}
                </span>
                <span className="text-xs text-slate-400">
                  {course_count} course{course_count !== 1 ? "s" : ""}
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Footer */}
      <footer className="border-t border-slate-200">
        <div className="max-w-4xl mx-auto px-6 py-8 flex flex-col sm:flex-row justify-between items-center gap-2 text-xs text-slate-400">
          <span>© {new Date().getFullYear()} PantherGrades</span>
          <span>
            Grade distributions reflect many factors. Use alongside other
            resources when making enrollment decisions.
          </span>
        </div>
      </footer>
    </main>
  );
}