import type { HydrationData } from "../../services/types";

interface HydrationBarProps {
  hydration: HydrationData;
}

export default function HydrationBar({ hydration }: HydrationBarProps) {
  const { current, goal } = hydration;
  const pct = Math.min((current / goal) * 100, 100);

  return (
    <div className="flex items-center gap-4 rounded-xl border border-[#f0f0f0] bg-white px-5 py-4">
      <p className="text-sm font-medium text-[#18181b]">Water</p>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#f0f0f0]">
        <div
          className="h-full rounded-full bg-[#3b82f6] transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-sm text-[#a1a1aa]">
        {current} / {goal}
      </p>
    </div>
  );
}
