import { CoachMessage } from '../types';

export async function getCoachMessages(): Promise<CoachMessage[]> {
  return [
    {
      id: 'c1',
      type: 'insight',
      label: 'Now',
      content:
        'Your protein is at 57% with dinner still ahead. A grilled fish or chicken dish would close the gap nicely.',
    },
    {
      id: 'c2',
      type: 'travel',
      label: 'Travel',
      content:
        'You have an early flight tomorrow at 6:40 AM. Consider prepping a high-protein breakfast you can grab on the way out.',
      actionLabel: 'Show suggestions',
    },
  ];
}
