export interface FoodEntry {
  id: string;
  name: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  logged_at: string;
  source: "manual" | "chat";
}

export interface DailySummary {
  date: string;
  total_calories: number;
  total_protein_g: number;
  total_carbs_g: number;
  total_fat_g: number;
  entry_count: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface FoodLogResponse {
  entries: FoodEntry[];
}

export interface ChatHistoryResponse {
  messages: ChatMessage[];
}

export interface ChatResponse {
  reply: string;
  created_entries: FoodEntry[];
}

export interface HealthResponse {
  status: "ok";
}

export interface CreateFoodEntryInput {
  name: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  logged_at: string;
}
