import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { getWeeklySummary } from "../../services/mock";
import type { DaySummary } from "../../services/types";

export default function WeekView() {
  const [days, setDays] = useState<DaySummary[]>([]);

  useEffect(() => {
    getWeeklySummary().then(setDays);
  }, []);

  if (days.length === 0) return null;

  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-xl border border-[#f0f0f0] bg-white p-6">
        <p className="mb-6 text-[11px] font-semibold uppercase tracking-wider text-[#a1a1aa]">
          Weekly Overview
        </p>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={days} barGap={2} barCategoryGap="20%">
              <XAxis
                dataKey="dayLabel"
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 12, fill: "#a1a1aa" }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 11, fill: "#a1a1aa" }}
                width={40}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#fff",
                  border: "1px solid #f0f0f0",
                  borderRadius: 8,
                  fontSize: 13,
                }}
                cursor={{ fill: "rgba(0,0,0,0.03)" }}
              />
              <Bar
                dataKey="calories"
                name="Calories"
                fill="#18181b"
                radius={[3, 3, 0, 0]}
              />
              <Bar
                dataKey="protein"
                name="Protein"
                fill="#6366f1"
                radius={[3, 3, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-xl border border-[#f0f0f0] bg-white px-5 py-4">
        <p className="text-sm leading-relaxed text-[#71717a]">
          Protein tends to drop mid-week during travel days.
        </p>
      </div>
    </div>
  );
}
