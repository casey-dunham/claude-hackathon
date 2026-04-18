import type { ReactNode } from "react";
import Sidebar from "./Sidebar";
import Header from "./Header";
import CoachPanel from "./CoachPanel";
import type { CoachMessage } from "../../services/types";

interface AppShellProps {
  children: ReactNode;
  activePage: string;
  onNavigate: (page: string) => void;
  userName?: string;
  date?: string;
  coachMessages?: CoachMessage[];
}

export default function AppShell({
  children,
  activePage,
  onNavigate,
  userName = "Adam",
  date = "Today",
  coachMessages = [],
}: AppShellProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-[#fafafa]">
      <Sidebar activePage={activePage} onNavigate={onNavigate} />

      <div className="flex flex-1 flex-col overflow-hidden">
        <Header userName={userName} date={date} />

        <div className="flex flex-1 overflow-hidden">
          <main className="flex-1 overflow-y-auto p-8">{children}</main>
          <CoachPanel messages={coachMessages} />
        </div>
      </div>
    </div>
  );
}
