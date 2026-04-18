import { useEffect, useState } from "react";
import MacroRow from "../dashboard/MacroRow";
import MealList from "../dashboard/MealList";
import HydrationBar from "../dashboard/HydrationBar";
import { getMacroSummary, getTodayMeals, getHydration } from "../../services/mock";
import type { MacroSummary, Meal, HydrationData } from "../../services/types";

export default function TodayView() {
  const [macros, setMacros] = useState<MacroSummary | null>(null);
  const [meals, setMeals] = useState<Meal[]>([]);
  const [hydration, setHydration] = useState<HydrationData | null>(null);

  useEffect(() => {
    getMacroSummary().then(setMacros);
    getTodayMeals().then(setMeals);
    getHydration().then(setHydration);
  }, []);

  if (!macros || !hydration) return null;

  return (
    <div className="flex flex-col gap-6">
      <MacroRow macros={macros} />
      <MealList meals={meals} limit={2} />
      <HydrationBar hydration={hydration} />
    </div>
  );
}
