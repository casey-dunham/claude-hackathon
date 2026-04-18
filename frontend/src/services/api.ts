import { ChatMessage, ChatResponse } from './types';

const BASE_URL = 'http://localhost:8000';

export async function sendChatMessage(message: string): Promise<ChatResponse> {
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error('Chat request failed');
  return res.json();
}

export async function getChatHistory(limit = 50): Promise<{ messages: ChatMessage[] }> {
  const res = await fetch(`${BASE_URL}/api/chat/history?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch chat history');
  return res.json();
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE_URL}/api/health`);
    return res.ok;
  } catch {
    return false;
  }
}
