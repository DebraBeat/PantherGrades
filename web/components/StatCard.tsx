interface StatCardProps {
  label: string;
  value: string | number | null;
  sub?: string;
  highlight?: "good" | "bad" | "neutral";
}

export default function StatCard({ label, value, sub, highlight = "neutral" }: StatCardProps) {
  const highlightClass = {
    good: "text-emerald-600",
    bad: "text-rose-600",
    neutral: "text-slate-800",
  }[highlight];

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col gap-1">
      <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">
        {label}
      </span>
      <span className={`text-3xl font-bold tabular-nums ${highlightClass}`}>
        {value ?? "—"}
      </span>
      {sub && <span className="text-xs text-slate-400 mt-1">{sub}</span>}
    </div>
  );
}