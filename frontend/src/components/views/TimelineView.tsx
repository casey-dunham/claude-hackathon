import { useEffect, useState } from "react";
import { getTimeline } from "../../services/mock";
import type { TimelineBlock } from "../../services/types";

const periodOrder = ["morning", "midday", "evening"] as const;

const periodLabels: Record<string, string> = {
  morning: "Morning",
  midday: "Midday",
  evening: "Evening",
};

export default function TimelineView() {
  const [blocks, setBlocks] = useState<TimelineBlock[]>([]);

  useEffect(() => {
    getTimeline().then(setBlocks);
  }, []);

  if (blocks.length === 0) return null;

  const grouped = periodOrder.map((period) => ({
    period,
    label: periodLabels[period],
    items: blocks.filter((b) => b.period === period),
  }));

  return (
    <div className="flex flex-col gap-8">
      {grouped.map((group) => (
        <div key={group.period}>
          <p className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-[#a1a1aa]">
            {group.label}
          </p>
          <div className="flex flex-col gap-2">
            {group.items.length === 0 ? (
              <div className="rounded-xl border border-dashed border-[#d4d4d8] px-5 py-4">
                <p className="text-sm text-[#a1a1aa]">No meals logged</p>
              </div>
            ) : (
              group.items.map((block) =>
                block.meal ? (
                  <div
                    key={block.id}
                    className="rounded-xl border border-[#f0f0f0] bg-white px-5 py-4"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-[#18181b]">
                          {block.meal.name}
                        </p>
                        <p className="mt-0.5 text-xs text-[#a1a1aa]">
                          {block.meal.time}
                        </p>
                      </div>
                      <p className="text-sm font-medium text-[#18181b]">
                        {block.meal.calories} kcal
                      </p>
                    </div>
                    <div className="mt-2 flex gap-4 text-xs text-[#a1a1aa]">
                      <span>P {block.meal.protein}g</span>
                      <span>C {block.meal.carbs}g</span>
                      <span>F {block.meal.fat}g</span>
                    </div>
                  </div>
                ) : (
                  <div
                    key={block.id}
                    className="rounded-xl border border-dashed border-[#d4d4d8] px-5 py-4"
                  >
                    <p className="text-sm font-medium text-[#a1a1aa]">
                      {block.label}
                    </p>
                    {block.suggestion && (
                      <p className="mt-1 text-sm leading-relaxed text-[#a1a1aa]">
                        {block.suggestion}
                      </p>
                    )}
                  </div>
                )
              )
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
