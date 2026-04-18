import { DaySummary } from '../types';

export async function getWeeklySummary(): Promise<DaySummary[]> {
  return [
    {
      date: '2026-04-13',
      dayLabel: 'Mon',
      calories: 2050,
      caloriesGoal: 2200,
      protein: 132,
      proteinGoal: 150,
    },
    {
      date: '2026-04-14',
      dayLabel: 'Tue',
      calories: 2180,
      caloriesGoal: 2200,
      protein: 141,
      proteinGoal: 150,
    },
    {
      date: '2026-04-15',
      dayLabel: 'Wed',
      calories: 1780,
      caloriesGoal: 2200,
      protein: 88,
      proteinGoal: 150,
    },
    {
      date: '2026-04-16',
      dayLabel: 'Thu',
      calories: 1650,
      caloriesGoal: 2200,
      protein: 76,
      proteinGoal: 150,
    },
    {
      date: '2026-04-17',
      dayLabel: 'Fri',
      calories: 2060,
      caloriesGoal: 2200,
      protein: 104,
      proteinGoal: 150,
    },
    {
      date: '2026-04-18',
      dayLabel: 'Sat',
      calories: 1420,
      caloriesGoal: 2200,
      protein: 85,
      proteinGoal: 150,
    },
    {
      date: '2026-04-19',
      dayLabel: 'Sun',
      calories: 0,
      caloriesGoal: 2200,
      protein: 0,
      proteinGoal: 150,
    },
  ];
}
