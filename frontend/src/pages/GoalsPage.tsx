const goals = [
  { label: "Calories", value: 2200, unit: "kcal" },
  { label: "Protein", value: 150, unit: "g" },
  { label: "Carbs", value: 250, unit: "g" },
  { label: "Fat", value: 70, unit: "g" },
];

export default function GoalsPage() {
  return (
    <div>
      <h2 className="mb-6 text-lg font-semibold text-[#18181b]">Macro Goals</h2>

      <div className="rounded-xl border border-[#f0f0f0] bg-white">
        <div className="divide-y divide-[#f0f0f0]">
          {goals.map((goal) => (
            <div key={goal.label} className="flex items-center justify-between px-5 py-4">
              <p className="text-sm font-medium text-[#18181b]">{goal.label}</p>
              <div className="flex items-center gap-2">
                <span className="rounded-lg border border-[#f0f0f0] bg-[#fafafa] px-3 py-1.5 text-sm font-medium text-[#18181b]">
                  {goal.value}
                </span>
                <span className="text-sm text-[#a1a1aa]">{goal.unit}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <p className="mt-4 text-xs text-[#a1a1aa]">
        Goal editing coming soon. Contact your coach to adjust targets.
      </p>
    </div>
  );
}
