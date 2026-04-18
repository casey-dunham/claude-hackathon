import { useEffect, useState } from "react";
import AppShell from "./components/layout/AppShell";
import Dashboard from "./pages/Dashboard";
import MealsPage from "./pages/MealsPage";
import GoalsPage from "./pages/GoalsPage";
import SettingsPage from "./pages/SettingsPage";
import { getUser, getCoachMessages } from "./services/mock";
import type { User, CoachMessage } from "./services/types";

export default function App() {
  const [activePage, setActivePage] = useState("dashboard");
  const [user, setUser] = useState<User | null>(null);
  const [coachMessages, setCoachMessages] = useState<CoachMessage[]>([]);

  useEffect(() => {
    getUser().then(setUser);
    getCoachMessages().then(setCoachMessages);
  }, []);

  if (!user) return null;

  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  let page: React.ReactNode;
  switch (activePage) {
    case "meals":
      page = <MealsPage />;
      break;
    case "goals":
      page = <GoalsPage />;
      break;
    case "settings":
      page = <SettingsPage />;
      break;
    default:
      page = <Dashboard />;
  }

  return (
    <AppShell
      activePage={activePage}
      onNavigate={setActivePage}
      userName={user.name}
      date={today}
      coachMessages={coachMessages}
    >
      {page}
    </AppShell>
  );
}
