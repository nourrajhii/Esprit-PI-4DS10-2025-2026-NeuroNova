import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

// ── Types ─────────────────────────────────────────────────────────────

export interface ForecastRequest {
  zone: string;
  type_bien: string;
  type_transaction: string;
  prix_estime_actuel: number;
  horizon_mois?: number;
}

export interface ForecastPoint {
  date: string;
  prix_predit: number;
  ic_bas: number | null;
  ic_haut: number | null;
}

export interface ForecastResume {
  prix_j12: number;
  prix_j24: number;
  variation_pct_12: number;
  variation_pct_24: number;
  tendance: "hausse" | "baisse" | "stable";
}

export interface ForecastResponse {
  zone: string;
  type_bien: string;
  type_transaction: string;
  modele_utilise: string;
  mape_test: number | null;
  serie_utilisee: string;
  points: ForecastPoint[];
  resume: ForecastResume;
}

export interface ZonesResponse {
  zones: string[];
  types_bien: string[];
  types_transaction: string[];
}

// ── API calls ─────────────────────────────────────────────────────────

export async function fetchForecast(request: ForecastRequest): Promise<ForecastResponse> {
  const { data } = await api.post<ForecastResponse>("/api/predict", request);
  return data;
}

export async function fetchZones(): Promise<ZonesResponse> {
  const { data } = await api.get<ZonesResponse>("/api/zones");
  return data;
}

export async function fetchHealth(): Promise<{ status: string; models_loaded: number }> {
  const { data } = await api.get("/api/health");
  return data;
}
