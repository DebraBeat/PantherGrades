"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { GradeLetterTotals } from "@/lib/api";

interface GradeChartProps {
  totals: GradeLetterTotals;
  totalStudents: number;
}

const GRADE_COLORS: Record<string, string> = {
  A: "#22c55e",
  B: "#84cc16",
  C: "#eab308",
  D: "#f97316",
  F: "#ef4444",
  WF: "#dc2626",
  W:  "#94a3b8",
};

export default function GradeChart({ totals, totalStudents }: GradeChartProps) {
  if (!totalStudents) return null;

  const data = [
    { grade: "A",  count: totals.grade_a ?? 0 },
    { grade: "B",  count: totals.grade_b ?? 0 },
    { grade: "C",  count: totals.grade_c ?? 0 },
    { grade: "D",  count: totals.grade_d ?? 0 },
    { grade: "F",  count: totals.grade_f ?? 0 },
    { grade: "WF", count: totals.wf ?? 0 },
    { grade: "W",  count: totals.w ?? 0 },
  ].map((d) => ({
    ...d,
    pct: totalStudents > 0 ? Math.round((d.count / totalStudents) * 100) : 0,
  }));

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <XAxis
            dataKey="grade"
            tick={{ fontSize: 13, fontWeight: 600, fill: "#64748b" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(v) => `${v}%`}
            tick={{ fontSize: 12, fill: "#94a3b8" }}
            axisLine={false}
            tickLine={false}
            domain={[0, 100]}
          />
          <Tooltip
            formatter={(value: number, name: string, props: { payload?: { count: number } }) => [
              `${value}% (${props.payload?.count ?? 0} students)`,
              "Share",
            ]}
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
  );
}