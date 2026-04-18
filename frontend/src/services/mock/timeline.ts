import { TimelineBlock } from '../types';

export async function getTimeline(): Promise<TimelineBlock[]> {
  return [
    {
      id: 't1',
      period: 'morning',
      label: 'Morning',
      meal: {
        id: 'm1',
        name: 'Airport oatmeal & black coffee',
        time: '7:15 AM',
        calories: 320,
        protein: 12,
        carbs: 54,
        fat: 7,
        logged: true,
      },
    },
    {
      id: 't2',
      period: 'midday',
      label: 'Midday',
      meal: {
        id: 'm2',
        name: 'Grilled chicken wrap from hotel cafe',
        time: '12:30 PM',
        calories: 580,
        protein: 38,
        carbs: 52,
        fat: 22,
        logged: true,
      },
    },
    {
      id: 't3',
      period: 'midday',
      label: 'Afternoon snack',
      meal: {
        id: 'm3',
        name: 'Trail mix & protein bar (on the go)',
        time: '3:45 PM',
        calories: 520,
        protein: 35,
        carbs: 56,
        fat: 19,
        logged: true,
      },
    },
    {
      id: 't4',
      period: 'evening',
      label: 'Evening',
      suggestion:
        'Try a grilled salmon bowl — it would cover your remaining protein and keep fats balanced for the day.',
    },
  ];
}
