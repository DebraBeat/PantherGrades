import Link from "next/link";
import { ArrowLeft, Database, BarChart2, AlertTriangle, RefreshCw } from "lucide-react";
import { ReactNode } from "react";
import React from "react";

const SECTIONS: { icon: React.ElementType; title: string; content: ReactNode }[] = [
  {
    icon: Database,
    title: "Data source",
    content: (
      <>
        All grade distribution data comes from official Georgia State University records, obtained through GSU&apos;s{" "}
        <a
          href="https://dssapex.gsu.edu/ords/f?p=140:1::::NO"
          target="_blank"
          rel="noopener noreferrer"
          className="underline text-blue-600 hover:text-blue-700"
        >
          public grade distribution portal
        </a>
        . The dataset covers Fall 2005 through Spring 2026 and includes over 262,000 course sections across more than 2,200 unique courses and 2,400 instructors.
      </>
    ),
  },
  {
    icon: BarChart2,
    title: "Methodology",
    content: `Grade distributions show the percentage of students earning each letter grade (A, B, C, D, F) as well as withdrawals (W) and withdraw-fails (WF) in each course section. The course average GPA is provided directly by GSU and uses a 4.30 scale where A+ = 4.30, A = 4.0, A− = 3.7, and so on. The DWF rate represents the percentage of students who received a D, withdrew with a failing grade (WF), or failed (F) — a standard at-risk metric used by GSU's academic advising office. Department averages are computed as weighted means across all graded sections in a department, weighted by enrollment.`,
  },
  {
    icon: AlertTriangle,
    title: "Limitations",
    content: `This data is aggregate only — no individual student records are used or displayed. Grade distributions reflect many interacting factors including course difficulty, student preparation, section size, semester timing, and instructional format (in-person vs. online). A low average GPA does not necessarily indicate poor teaching, and a high average GPA does not necessarily indicate an easy course. Comparisons between courses in different departments should be made with caution. This data is intended as one of many tools to inform enrollment decisions, not as a definitive evaluation of any course or instructor.`,
  },
  {
    icon: RefreshCw,
    title: "Updates",
    content: `The dataset is updated each semester when GSU releases new grade distribution reports, typically 6–8 weeks after the end of the semester. Course titles are sourced from the GSU course catalog. Some courses in the grade distribution data may not appear in the current catalog if they have been discontinued or renamed.`,
  },
];

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-slate-50">
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center gap-4">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Link>
          <span className="text-slate-300">|</span>
          <span className="font-semibold text-slate-800">About the data</span>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-12 flex flex-col gap-10">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
            About PantherGrades
          </h1>
          <p className="text-slate-500 mt-2 leading-relaxed">
            PantherGrades is an independent student resource built on publicly
            available GSU grade distribution data. It is not affiliated with or
            endorsed by Georgia State University.
          </p>
        </div>

        {SECTIONS.map(({ icon: Icon, title, content }) => (
          <div key={title} className="bg-white rounded-2xl border border-slate-200 p-7 flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                <Icon className="w-5 h-5 text-blue-600" />
              </div>
              <h2 className="text-lg font-bold text-slate-800">{title}</h2>
            </div>
            <p className="text-slate-600 leading-relaxed text-sm">{content}</p>
          </div>
        ))}

        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 text-sm text-amber-800 leading-relaxed">
          <strong>Note:</strong> Grade distributions are a snapshot of historical outcomes, not a prediction of your personal performance. Many students succeed in courses with high DWF rates, and many struggle in courses with high average GPAs. Use this data alongside your advisor&apos;s guidance, course reviews, and your own academic preparation.
        </div>
      </div>

      <footer className="border-t border-slate-200 mt-8">
        <div className="max-w-3xl mx-auto px-6 py-6 text-xs text-slate-400 text-center">
          Data sourced from official GSU grade distribution records · 2005–2026 ·{" "}
          <Link href="/" className="hover:text-slate-600 underline">
            Back to search
          </Link>
        </div>
      </footer>
    </main>
  );
}