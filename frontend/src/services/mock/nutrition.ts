import { MacroSummary } from '../types';

export async function getMacroSummary(): Promise<MacroSummary> {
  return {
    calories: { current: 1420, goal: 2200 },
    protein: { current: 85, goal: 150 },
    carbs: { current: 162, goal: 250 },
    fat: { current: 48, goal: 70 },
  };
}
