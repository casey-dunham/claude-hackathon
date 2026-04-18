import { useEffect, useState } from "react";
import { getAllMeals } from "../services/mock";
import type { Meal } from "../services/types";

function formatDate(isoTime: string): string {
  const date = new Date(isoTime);
  return date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
  });
}

function formatTime(isoTime: string): string {
  const date = new Date(isoTime);
  return date.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function MealsPage() {
  const [meals, setMeals] = useState<Meal[]>([]);

  useEffect(() => {
    getAllMeals().then(setMeals);
  }, []);

  // Group meals by date
  const grouped = meals.reduce<Record<string, Meal[]>>((acc, meal) => {
    const dateKey = formatDate(meal.time);
    if (!acc[dateKey]) acc[dateKey] = [];
    acc[dateKey].push(meal);
    return acc;
  }, {});

  const dateKeys = Object.keys(grouped);

  return (
    <div>
      <h2 className="mb-6 text-lg font-semibold text-[#18181b]">Meal History</h2>

      <div className="flex flex-col gap-8">
        {dateKeys.map((dateLabel) => (
          <div key={dateLabel}>
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-[#a1a1aa]">
              {dateLabel}
            </p>
            <div className="flex flex-col gap-2">
              {grouped[dateLabel].map((meal) => (
                <div
                  key={meal.id}
                  className="rounded-xl border border-[#f0f0f0] bg-white px-5 py-4"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-[#18181b]">
                        {meal.name}
                      </p>
                      <p className="mt-0.5 text-xs text-[#a1a1aa]">
                        {formatTime(meal.time)}
                      </p>
                    </div>
                    <div className="text-right">
                      {meal.logged ? (
                        <p className="text-sm font-medium text-[#18181b]">
                          {meal.calories} kcal
                        </p>
                      ) : (
                        <span className="text-xs font-medium text-[#a1a1aa]">
                          Not logged
                        </span>
                      )}
                    </div>
                  </div>
                  {meal.logged && (
                    <div className="mt-2 flex gap-4 text-xs text-[#a1a1aa]">
                      <span>Protein {meal.protein}g</span>
                      <span>Carbs {meal.carbs}g</span>
                      <span>Fat {meal.fat}g</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
