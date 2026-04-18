export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface PromptRequest {
  prompt: string;
  conversation_history?: ChatMessage[];
}

export interface AdvisorCriteria {
  transaction_type: string | null;
  category: string | null;
  city: string | null;
  region: string | null;
  min_price: number | null;
  max_price: number | null;
  rooms: number | null;
  min_size: number | null;
  max_size: number | null;
}

export interface PropertyItem {
  id: string;
  title: string;
  price: number;
  city?: string | null;
  region?: string | null;
  property_type?: string | null;
  surface_m2?: number | null;
  size?: number | null;
  rooms?: number | null;
  room_count?: number | null;
  bathrooms?: number | null;
  bathroom_count?: number | null;
  transaction_type?: string | null;
  url?: string | null;
  listing_url?: string | null;
  category?: string | null;
  detected_category?: string | null;
  detected_sub_type?: string | null;
  score?: number | null;
  price_per_m2?: number | null;
}

export interface MarketStats {
  avg_price?: number | null;
  min_price?: number | null;
  max_price?: number | null;
  median_price?: number | null;
  avg_size?: number | null;
  avg_price_per_m2?: number | null;
  count?: number;
}

export interface PromptResponse {
  natural_response: string;
  advice: string;
  criteria: AdvisorCriteria | Record<string, never>;
  is_real_estate_query: boolean;
  properties: PropertyItem[];
  total_found: number;
  market_stats: MarketStats;
}