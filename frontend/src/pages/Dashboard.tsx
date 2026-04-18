import { useState } from "react";
import TodayView from "../components/views/TodayView";
import WeekView from "../components/views/WeekView";
import TimelineView from "../components/views/TimelineView";

const tabs = [
  { id: "today", label: "Today" },
  { id: "week", label: "Week" },
  { id: "timeline", label: "Timeline" },
] as const;

type TabId = (typeof tabs)[number]["id"];

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<TabId>("today");

  return (
    <div>
      <div className="mb-6 flex gap-6 border-b border-[#f0f0f0]">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`pb-3 text-sm font-medium transition-colors ${
                isActive
                  ? "border-b-2 border-[#18181b] text-[#18181b]"
                  : "text-[#a1a1aa] hover:text-[#71717a]"
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {activeTab === "today" && <TodayView />}
      {activeTab === "week" && <WeekView />}
      {activeTab === "timeline" && <TimelineView />}
    </div>
  );
}
