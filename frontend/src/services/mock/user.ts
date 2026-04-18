import { User } from '../types';

export async function getUser(): Promise<User> {
  return {
    id: '1',
    name: 'Adam',
    initials: 'A',
    plan: 'Pro Plan',
  };
}
