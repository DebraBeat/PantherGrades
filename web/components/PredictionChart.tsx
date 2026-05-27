"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";

interface GradePrediction {
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

interface PredictionChartProps {
  predictions: GradePrediction[];
}

const GRADE_COLORS: Record<string, string> = {
  A: "#22c55e",
  B: "#84cc16",
  C: "#eab308",
  D: "#f97316",
  F: "#ef4444",
  W: "#94a3b8",
};

const CONFIDENCE_STYLES: Record<string, { label: string; color: string; bg: string }> = {
  high:   { label: "High confidence",   color: "text-emerald-700", bg: "bg-emerald-50 border-emerald-200" },
  medium: { label: "Medium confidence", color: "text-amber-700",   bg: "bg-amber-50 border-amber-200"   },
  low:    { label: "Low confidence",    color: "text-rose-700",    bg: "bg-rose-50 border-rose-200"     },
};

function termToLabel(term: string): string {
  if (!term || term.length < 6) return term;
  const year = term.slice(0, 4);
  const month = term.slice(4, 6);
  const sem = month === "08" ? "Fall" : month === "01" ? "Spring" : "Summer";
  return `${sem} ${year}`;
}

function topGrade(pred: GradePrediction): string {
  const grades = [
    { label: "A", val: pred.pred_a },
    { label: "B", val: pred.pred_b },
    { label: "C", val: pred.pred_c },
    { label: "D", val: pred.pred_d },
    { label: "F", val: pred.pred_f },
  ].filter((g) => g.val != null);
  if (!grades.length) return "unknown";
  return grades.sort((a, b) => (b.val ?? 0) - (a.val ?? 0))[0].label;
}

export default function PredictionChart({ predictions }: PredictionChartProps) {
  // Show "all" prediction by default, fall back to first available
  const pred =
    predictions.find((p) => p.instruction_method === "all") ?? predictions[0];

  if (!pred) return null;

  const data = [
    { grade: "A", pct: (pred.pred_a ?? 0) * 100 },
    { grade: "B", pct: (pred.pred_b ?? 0) * 100 },
    { grade: "C", pct: (pred.pred_c ?? 0) * 100 },
    { grade: "D", pct: (pred.pred_d ?? 0) * 100 },
    { grade: "F", pct: (pred.pred_f ?? 0) * 100 },
    { grade: "W", pct: (pred.pred_w ?? 0) * 100 },
  ];

  const conf = pred.confidence ?? "low";
  const confStyle = CONFIDENCE_STYLES[conf] ?? CONFIDENCE_STYLES.low;
  const top = topGrade(pred);
  const hasSeparateMethod = predictions.length > 1;

  return (
    <div className="flex flex-col gap-4">
      {/* Summary sentence */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <p className="text-sm text-slate-600 leading-relaxed max-w-lg">
          Based on{" "}
          <span className="font-semibold">{pred.n_sections} sections</span> and{" "}
          <span className="font-semibold">
            {pred.n_students?.toLocaleString()} students
          </span>{" "}
          through {termToLabel(pred.latest_term ?? "")}, students in this course most
          commonly earn a{" "}
          <span className="font-semibold text-slate-800">{top}</span>
          {pred.pred_gpa != null && (
            <>
              {" "}with a predicted average GPA of{" "}
              <span className="font-semibold text-slate-800">
                {pred.pred_gpa.toFixed(2)}
              </span>
            </>
          )}
          .
        </p>
        <span
          className={`text-xs font-medium px-2.5 py-1 rounded-lg border flex-shrink-0 ${confStyle.bg} ${confStyle.color}`}
        >
          {confStyle.label}
        </span>
      </div>

      {/* Bar chart */}
      <div className="w-full h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
            <XAxis
              dataKey="grade"
              tick={{ fontSize: 13, fontWeight: 600, fill: "#64748b" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tickFormatter={(v) => `${v.toFixed(0)}%`}
              tick={{ fontSize: 12, fill: "#94a3b8" }}
              axisLine={false}
              tickLine={false}
              domain={[0, 100]}
            />
            <Tooltip
              formatter={(value) => [`${Number(value).toFixed(1)}%`, "Predicted probability"]}
              contentStyle={{
                borderRadius: "12px",
                border: "1px solid #e2e8f0",
                fontSize: "13px",
              }}
            />
            <Bar dataKey="pct" radius={[6, 6, 0, 0]}>
              {data.map((entry) => (
                <Cell key={entry.grade} fill={GRADE_COLORS[entry.grade] ?? "#94a3b8"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Method breakdown if available */}
      {hasSeparateMethod && (
        <div className="flex gap-3 flex-wrap">
          {predictions
            .filter((p) => p.instruction_method !== "all")
            .map((p) => (
              <div
                key={p.instruction_method}
                className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-600"
              >
                <span className="capitalize font-medium">
                  {p.instruction_method.replace("_", " ")}:
                </span>
                <span>GPA {p.pred_gpa?.toFixed(2) ?? "—"}</span>
                <span className="text-slate-400">·</span>
                <span>{p.n_sections} sections</span>
              </div>
            ))}
        </div>
      )}

      <p className="text-xs text-slate-400">
        Predictions are computed using exponentially-weighted historical data,
        giving more weight to recent semesters. This is not a guarantee of your
        personal grade outcome.
      </p>
    </div>
  );
}