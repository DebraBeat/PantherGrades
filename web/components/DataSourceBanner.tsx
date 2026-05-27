import Link from "next/link";
import { Info } from "lucide-react";

export default function DataSourceBanner() {
  return (
    <div className="flex items-start gap-3 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-xs text-slate-500">
      <Info className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />
      <p className="leading-relaxed">
        Data from <a href="https://dssapex.gsu.edu/ords/f?p=140:1::::NO">official GSU grade distribution records</a>· 2005–2026 · Aggregate only — no individual student records.
        GPA uses a 4.30 scale. DWF rate = % of students with D, WF, or F.{" "}
        <Link href="/about" className="underline hover:text-slate-700 transition-colors">
          Learn more
        </Link>
      </p>
    </div>
  );
}