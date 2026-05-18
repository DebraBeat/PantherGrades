"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { TrendPoint } from "@/lib/api";

interface TrendChartProps {
  data: TrendPoint[];
  deptAvgGpa?: number | null;
}

export default function TrendChart({ data, deptAvgGpa }: TrendChartProps) {
  const formatted = data.map((d) => ({
    ...d,
    label: `${d.semester.slice(0, 2)} ${String(d.year).slice(2)}`,
  }));

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={formatted} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[1.5, 4.33]}
            tick={{ fontSize: 12, fill: "#94a3b8" }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => v.toFixed(1)}
          />
          <Tooltip
            formatter={(value: number) => [value.toFixed(2), "Avg GPA"]}
            contentStyle={{
              borderRadius: "12px",
              border: "1px solid #e2e8f0",
              fontSize: "13px",
            }}
          />
          {deptAvgGpa && (
            <ReferenceLine
              y={deptAvgGpa}
              stroke="#94a3b8"
              strokeDasharray="4 4"
              label={{
                value: `Dept avg ${deptAvgGpa.toFixed(2)}`,
                position: "insideTopRight",
                fontSize: 11,
                fill: "#94a3b8",
              }}
            />
          )}
          <Line
            type="monotone"
            dataKey="avg_gpa"
            stroke="#3b82f6"
            strokeWidth={2.5}
            dot={{ r: 3, fill: "#3b82f6" }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}