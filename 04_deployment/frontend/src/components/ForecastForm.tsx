import React, { useEffect, useState } from "react";
import { fetchZones, type ForecastRequest } from "../services/api.service";

interface Props {
  onSubmit: (req: ForecastRequest) => void;
  loading: boolean;
}

const DEFAULT_ZONES = ["Tunis", "Sfax", "Sousse", "Nabeul", "Ariana", "Ben Arous", "Monastir", "Bizerte", "Hammamet"];
const DEFAULT_TYPES = ["appartement", "villa", "maison", "terrain", "bureau"];

export default function ForecastForm({ onSubmit, loading }: Props) {
  const [zones, setZones] = useState<string[]>(DEFAULT_ZONES);
  const [typesBien, setTypesBien] = useState<string[]>(DEFAULT_TYPES);

  const [zone, setZone] = useState("Tunis");
  const [typeBien, setTypeBien] = useState("appartement");
  const [typeTransaction, setTypeTransaction] = useState("vente");
  const [prix, setPrix] = useState<string>("3500");
  const [horizon, setHorizon] = useState(24);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchZones()
      .then((data) => {
        if (data.zones.length) setZones(data.zones);
        if (data.types_bien.length) setTypesBien(data.types_bien);
      })
      .catch(() => {
        // garder les valeurs par défaut
      });
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const p = parseFloat(prix);
    if (!prix || isNaN(p) || p <= 0) {
      setError("Veuillez saisir un prix valide (> 0 TND/m²).");
      return;
    }
    setError(null);
    onSubmit({
      zone,
      type_bien: typeBien,
      type_transaction: typeTransaction,
      prix_estime_actuel: p,
      horizon_mois: horizon,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-md p-6 space-y-5">
      <h2 className="text-xl font-semibold text-slate-800">Paramètres du bien</h2>

      {/* Zone */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Gouvernorat</label>
        <select
          value={zone}
          onChange={(e) => setZone(e.target.value)}
          className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {zones.map((z) => (
            <option key={z} value={z}>{z}</option>
          ))}
        </select>
      </div>

      {/* Type bien */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Type de bien</label>
        <select
          value={typeBien}
          onChange={(e) => setTypeBien(e.target.value)}
          className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {typesBien.map((t) => (
            <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
          ))}
        </select>
      </div>

      {/* Type transaction */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Transaction</label>
        <div className="flex gap-3">
          {["vente", "location"].map((tx) => (
            <label key={tx} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="transaction"
                value={tx}
                checked={typeTransaction === tx}
                onChange={() => setTypeTransaction(tx)}
                className="accent-blue-600"
              />
              <span className="text-sm capitalize">{tx}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Prix actuel */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Prix estimé actuel <span className="text-slate-400">(TND/m²)</span>
        </label>
        <input
          type="number"
          value={prix}
          onChange={(e) => setPrix(e.target.value)}
          min="1"
          step="50"
          placeholder="ex: 3500"
          className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
      </div>

      {/* Horizon */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Horizon de prévision : <span className="font-semibold text-blue-600">{horizon} mois</span>
        </label>
        <input
          type="range"
          min={6}
          max={48}
          step={6}
          value={horizon}
          onChange={(e) => setHorizon(Number(e.target.value))}
          className="w-full accent-blue-600"
        />
        <div className="flex justify-between text-xs text-slate-400 mt-1">
          <span>6 mois</span><span>24 mois</span><span>48 mois</span>
        </div>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold rounded-xl py-3 transition-colors"
      >
        {loading ? "Calcul en cours…" : "Prévoir l'évolution"}
      </button>
    </form>
  );
}
