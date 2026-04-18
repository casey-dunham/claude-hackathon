import type { MacroSummary } from "../../services/types";

interface MacroRowProps {
  macros: MacroSummary;
}

const macroConfig = [
  { key: "calories" as const, label: "Calories", unit: "kcal", color: "bg-[#18181b]" },
  { key: "protein" as const, label: "Protein", unit: "g", color: "bg-[#6366f1]" },
  { key: "carbs" as const, label: "Carbs", unit: "g", color: "bg-[#8b5cf6]" },
  { key: "fat" as const, label: "Fat", unit: "g", color: "bg-[#f59e0b]" },
];

export default function MacroRow({ macros }: MacroRowProps) {
  return (
    <div className="grid grid-cols-4 gap-px overflow-hidden rounded-xl bg-[#f0f0f0]">
      {macroConfig.map(({ key, label, unit, color }) => {
        const { current, goal } = macros[key];
        const pct = Math.min((current / goal) * 100, 100);

        return (
          <div key={key} className="bg-white p-5">
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-[#a1a1aa]">
              {label}
            </p>
            <p className="text-2xl font-semibold text-[#18181b]">
              {current}
              <span className="ml-1 text-sm font-normal text-[#a1a1aa]">
                / {goal} {unit}
              </span>
            </p>
            <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-[#f0f0f0]">
              <div
                className={`h-full rounded-full ${color} transition-all`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
