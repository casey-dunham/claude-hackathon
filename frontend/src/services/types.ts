export interface User {
  id: string;
  name: string;
  initials: string;
  plan: string;
}

export interface MacroSummary {
  calories: { current: number; goal: number };
  protein: { current: number; goal: number };
  carbs: { current: number; goal: number };
  fat: { current: number; goal: number };
}

export interface Meal {
  id: string;
  name: string;
  time: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  logged: boolean;
}

export interface HydrationData {
  current: number;
  goal: number;
}

export interface CoachMessage {
  id: string;
  type: 'insight' | 'travel' | 'pattern';
  label: string;
  content: string;
  actionLabel?: string;
}

export interface DaySummary {
  date: string;
  dayLabel: string;
  calories: number;
  caloriesGoal: number;
  protein: number;
  proteinGoal: number;
}

export interface TimelineBlock {
  id: string;
  period: 'morning' | 'midday' | 'evening';
  label: string;
  meal?: Meal;
  suggestion?: string;
}
