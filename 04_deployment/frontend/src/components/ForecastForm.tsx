import React, { useEffect, useState } from "react";
import {
  fetchZones,
  type VenteRequest,
  type LocationRequest,
} from "../services/api.service";

type Mode = "vente" | "location";

interface Props {
  onSubmitVente: (req: VenteRequest) => void;
  onSubmitLocation: (req: LocationRequest) => void;
  loading: boolean;
}

const DEFAULT_GOUVERNORATS = [
  "Tunis", "Ariana", "Ben Arous", "Manouba",
  "Nabeul", "Zaghouan", "Bizerte",
  "Béja", "Jendouba", "Kef", "Siliana",
  "Sousse", "Monastir", "Mahdia",
  "Sfax",
  "Kairouan", "Kasserine", "Sidi Bouzid",
  "Gabès", "Medenine", "Tataouine",
  "Gafsa", "Tozeur", "Kébili",
];
const DEFAULT_TYPES = ["appartement", "villa", "maison", "terrain", "bureau"];
const DEFAULT_COMPOSITIONS = ["S+1", "S+2", "S+3", "S+4"];

export default function ForecastForm({ onSubmitVente, onSubmitLocation, loading }: Props) {
  const [mode, setMode] = useState<Mode>("vente");
  const [gouvernorats, setGouvernorats] = useState<string[]>(DEFAULT_GOUVERNORATS);
  const [typesBien, setTypesBien] = useState<string[]>(DEFAULT_TYPES);

  // Champs communs
  const [gouvernorat, setGouvernorat] = useState("Tunis");

  // Champs vente
  const [typeBien, setTypeBien] = useState("appartement");
  const [superficie, setSuperficie] = useState<string>("90");
  const [prixM2, setPrixM2] = useState<string>("3500");

  // Champs location
  const [composition, setComposition] = useState("S+2");
  const [loyer, setLoyer] = useState<string>("1200");

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchZones()
      .then((data) => {
        if (data.gouvernorats.length) setGouvernorats(data.gouvernorats);
        if (data.types_bien.length) setTypesBien(data.types_bien);
      })
      .catch(() => {/* garder les valeurs par défaut */});
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (mode === "vente") {
      const s = parseFloat(superficie);
      const p = parseFloat(prixM2);
      if (!superficie || isNaN(s) || s <= 0) {
        setError("Superficie invalide (doit être > 0 m²).");
        return;
      }
      if (!prixM2 || isNaN(p) || p <= 0) {
        setError("Prix au m² invalide (doit être > 0 TND).");
        return;
      }
      onSubmitVente({ gouvernorat, type_bien: typeBien, superficie: s, prix_m2_saisi: p });
    } else {
      const l = parseFloat(loyer);
      if (!loyer || isNaN(l) || l <= 0) {
        setError("Loyer invalide (doit être > 0 TND).");
        return;
      }
      onSubmitLocation({ gouvernorat, composition, loyer_saisi: l });
    }
  }

  const inputCls = "w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";
  const labelCls = "block text-sm font-medium text-slate-700 mb-1";

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-md p-6 space-y-5">
      <h2 className="text-xl font-semibold text-slate-800">Paramètres du bien</h2>

      {/* Mode toggle */}
      <div>
        <label className={labelCls}>Mode d'analyse</label>
        <div className="flex rounded-lg overflow-hidden border border-slate-300">
          {(["vente", "location"] as Mode[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => { setMode(m); setError(null); }}
              className={`flex-1 py-2 text-sm font-semibold transition-colors ${
                mode === m
                  ? "bg-blue-600 text-white"
                  : "bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              {m === "vente" ? "Vente (prix/m²)" : "Location (loyer)"}
            </button>
          ))}
        </div>
      </div>

      {/* Gouvernorat */}
      <div>
        <label className={labelCls}>Gouvernorat</label>
        <select
          value={gouvernorat}
          onChange={(e) => setGouvernorat(e.target.value)}
          className={inputCls}
        >
          {gouvernorats.map((g) => (
            <option key={g} value={g}>{g}</option>
          ))}
        </select>
      </div>

      {/* ── Champs VENTE ── */}
      {mode === "vente" && (
        <>
          <div>
            <label className={labelCls}>Type de bien</label>
            <select
              value={typeBien}
              onChange={(e) => setTypeBien(e.target.value)}
              className={inputCls}
            >
              {typesBien.map((t) => (
                <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
              ))}
            </select>
          </div>

          <div>
            <label className={labelCls}>
              Superficie <span className="text-slate-400">(m²)</span>
            </label>
            <input
              type="number"
              value={superficie}
              onChange={(e) => setSuperficie(e.target.value)}
              min="1"
              step="any"
              placeholder="ex: 90"
              className={inputCls}
            />
          </div>

          <div>
            <label className={labelCls}>
              Prix au m² <span className="text-slate-400">(TND/m²)</span>
            </label>
            <input
              type="number"
              value={prixM2}
              onChange={(e) => setPrixM2(e.target.value)}
              min="1"
              step="any"
              placeholder="ex: 3500"
              className={inputCls}
            />
          </div>
        </>
      )}

      {/* ── Champs LOCATION ── */}
      {mode === "location" && (
        <>
          <div>
            <label className={labelCls}>Composition du logement</label>
            <div className="grid grid-cols-4 gap-2">
              {DEFAULT_COMPOSITIONS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setComposition(c)}
                  className={`py-2 rounded-lg text-sm font-semibold border transition-colors ${
                    composition === c
                      ? "bg-blue-600 text-white border-blue-600"
                      : "bg-white text-slate-600 border-slate-300 hover:border-blue-400"
                  }`}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className={labelCls}>
              Loyer mensuel actuel <span className="text-slate-400">(TND)</span>
            </label>
            <input
              type="number"
              value={loyer}
              onChange={(e) => setLoyer(e.target.value)}
              min="1"
              step="any"
              placeholder="ex: 1200"
              className={inputCls}
            />
          </div>
        </>
      )}

      {error && <p className="text-red-500 text-xs">{error}</p>}

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold rounded-xl py-3 transition-colors"
      >
        {loading ? "Analyse en cours…" : "Lancer l'analyse"}
      </button>
    </form>
  );
}
