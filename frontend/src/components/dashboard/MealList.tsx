import type { Meal } from "../../services/types";

interface MealListProps {
  meals: Meal[];
  limit?: number;
}

const dotColors = [
  "bg-[#6366f1]",
  "bg-[#8b5cf6]",
  "bg-[#f59e0b]",
  "bg-[#22c55e]",
  "bg-[#3b82f6]",
];

export default function MealList({ meals, limit = 2 }: MealListProps) {
  const visible = meals.slice(0, limit);

  return (
    <div>
      <p className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-[#a1a1aa]">
        Recent
      </p>

      <div className="flex flex-col gap-2">
        {visible.map((meal, i) => (
          <div
            key={meal.id}
            className="flex items-center justify-between rounded-xl border border-[#f0f0f0] bg-white px-5 py-4 transition-colors hover:border-[#d4d4d8]"
          >
            <div className="flex items-center gap-3">
              <span
                className={`h-2 w-2 shrink-0 rounded-full ${dotColors[i % dotColors.length]}`}
              />
              <div>
                <p className="text-sm font-medium text-[#18181b]">
                  {meal.name}
                </p>
                <p className="text-xs text-[#a1a1aa]">{meal.time}</p>
              </div>
            </div>
            <p className="text-sm font-medium text-[#18181b]">
              {meal.calories} kcal
            </p>
          </div>
        ))}
      </div>

      <button className="mt-3 text-sm font-medium text-[#6366f1] hover:text-[#4f46e5]">
        View all meals &rarr;
      </button>
    </div>
  );
}
