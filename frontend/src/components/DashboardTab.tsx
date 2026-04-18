import { useEffect, useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { getDashboardHistory, getTodaySummary } from '../services/api';
import type { DailySummary } from '../services/types';

function shortDate(isoDate: string): string {
  const [, month, day] = isoDate.split('-');
  return `${parseInt(month)}/${parseInt(day)}`;
}

function StatCard({ label, value, unit }: { label: string; value: number; unit: string }) {
  return (
    <div className="rounded-xl border border-[#f0f0f0] bg-white p-4">
      <p className="text-xs text-[#a1a1aa]">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-[#18181b]">
        {value}
        <span className="ml-1 text-sm font-normal text-[#71717a]">{unit}</span>
      </p>
    </div>
  );
}

export default function DashboardTab() {
  const [today, setToday] = useState<DailySummary | null>(null);
  const [history, setHistory] = useState<DailySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [todayData, historyData] = await Promise.all([
          getTodaySummary(),
          getDashboardHistory(7),
        ]);
        setToday(todayData);
        setHistory(historyData.days);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load dashboard');
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  if (loading) return <p className="text-sm text-[#a1a1aa]">Loading dashboard...</p>;
  if (error) return <p className="text-sm text-[#b91c1c]">{error}</p>;

  const chartData = history.map((d) => ({
    date: shortDate(d.date),
    Calories: d.total_calories,
    Protein: Math.round(d.total_protein_g),
    Carbs: Math.round(d.total_carbs_g),
    Fat: Math.round(d.total_fat_g),
  }));

  return (
    <div className="space-y-6">
      {today && (
        <div>
          <h2 className="mb-3 text-sm font-medium text-[#18181b]">Today</h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="Calories" value={today.total_calories} unit="kcal" />
            <StatCard label="Protein" value={Math.round(today.total_protein_g)} unit="g" />
            <StatCard label="Carbs" value={Math.round(today.total_carbs_g)} unit="g" />
            <StatCard label="Fat" value={Math.round(today.total_fat_g)} unit="g" />
          </div>
        </div>
      )}

      <div className="rounded-xl border border-[#f0f0f0] bg-white p-5">
        <h2 className="mb-4 text-sm font-medium text-[#18181b]">Calories — Last 7 Days</h2>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="Calories"
              stroke="#18181b"
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="rounded-xl border border-[#f0f0f0] bg-white p-5">
        <h2 className="mb-4 text-sm font-medium text-[#18181b]">Macros — Last 7 Days</h2>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Bar dataKey="Protein" fill="#3b82f6" radius={[3, 3, 0, 0]} />
            <Bar dataKey="Carbs" fill="#f59e0b" radius={[3, 3, 0, 0]} />
            <Bar dataKey="Fat" fill="#ef4444" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
