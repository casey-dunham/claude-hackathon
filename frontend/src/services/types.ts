export interface NearbyPlace {
  id: string;
  name: string;
  type: 'restaurant' | 'cafe' | 'grocery' | 'deli' | 'food_truck' | 'juice_bar';
  lat: number;
  lng: number;
  distance_m: number;
  address: string;
  rating: number;
  price_level: number; // 1-3
  is_open: boolean;
}

export interface Recommendation {
  id: string;
  place_id: string;
  place_name: string;
  item_name: string;
  description: string;
  estimated_calories: number;
  estimated_protein_g: number;
  estimated_carbs_g: number;
  estimated_fat_g: number;
  estimated_price_usd: number;
  tags: string[];
  distance_m: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface ChatResponse {
  reply: string;
  created_entries: any[];
}
