import { HydrationData } from '../types';

export async function getHydration(): Promise<HydrationData> {
  return {
    current: 5,
    goal: 8,
  };
}
