import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

// ── Types communs ──────────────────────────────────────────────────────────────

export interface ForecastPoint {
  date: string;
  prix_predit: number;
  ic_bas: number | null;
  ic_haut: number | null;
}

export interface HorizonData {
  valeur: number;
  variation_pct: number;
}

// ── Réponse agent (vente & location) ─────────────────────────────────────────

export interface AgentResponse {
  mode: "vente" | "location";
  gouvernorat: string;
  type_bien: string | null;        // vente uniquement
  composition: string | null;      // location uniquement
  superficie: number | null;       // vente uniquement
  valeur_saisie: number;
  valeur_totale_actuelle: number | null; // vente uniquement
  prix_moyen_marche: number;
  diff_vs_marche_pct: number;
  statut_prix: string;
  taux_mensuel: number;
  taux_annuel: number;             // en %
  horizons: {
    "6": HorizonData;
    "12": HorizonData;
    "18": HorizonData;
    "24": HorizonData;
  };
  tendance: "hausse" | "baisse" | "stable";
  risque: "Faible" | "Modéré" | "Élevé";
  tension: string;
  analyse_marche: string;
  facteurs: string[];
  recommandation: string;
  points: ForecastPoint[];
}

// ── Requêtes ──────────────────────────────────────────────────────────────────

export interface VenteRequest {
  gouvernorat: string;
  type_bien: string;
  superficie: number;
  prix_m2_saisi: number;
}

export interface LocationRequest {
  gouvernorat: string;
  composition: string;
  loyer_saisi: number;
}

// ── Zones de référence ────────────────────────────────────────────────────────

export interface ZonesResponse {
  gouvernorats: string[];
  types_bien: string[];
  compositions: string[];
}

// ── Appels API ────────────────────────────────────────────────────────────────

export async function analyzeVente(req: VenteRequest): Promise<AgentResponse> {
  const { data } = await api.post<AgentResponse>("/api/analyze/vente", req);
  return data;
}

export async function analyzeLocation(req: LocationRequest): Promise<AgentResponse> {
  const { data } = await api.post<AgentResponse>("/api/analyze/location", req);
  return data;
}

export async function fetchZones(): Promise<ZonesResponse> {
  const { data } = await api.get<ZonesResponse>("/api/zones");
  return data;
}

export async function fetchHealth(): Promise<{ status: string; gouvernorats: number }> {
  const { data } = await api.get("/api/health");
  return data;
}
