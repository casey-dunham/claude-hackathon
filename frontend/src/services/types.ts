export interface NearbyPlace {
  id: string;
  name: string;
  lat: number;
  lng: number;
  address: string;
  rating: number | null;
  user_ratings_total: number | null;
  price_level: number | null;
  is_open: boolean | null;
  distance_m: number;
  maps_url: string;
}

export interface NearbyPlacesResponse {
  places: NearbyPlace[];
}

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

export interface ChatContextInput {
  lat?: number;
  lng?: number;
  timezone?: string;
  local_time?: string;
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

export interface Profile {
  calorie_goal: number | null;
  protein_goal_g: number | null;
  carbs_goal_g: number | null;
  fat_goal_g: number | null;
  dietary_restrictions: string[];
}

export interface CreateFoodEntryInput {
  name: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  logged_at: string;
}
