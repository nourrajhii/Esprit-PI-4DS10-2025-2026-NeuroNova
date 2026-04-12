import { useState } from "react";
import ForecastForm from "./components/ForecastForm";
import ForecastChart from "./components/ForecastChart";
import ResultCard from "./components/ResultCard";
import { fetchForecast, type ForecastRequest, type ForecastResponse } from "./services/api.service";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastRequest, setLastRequest] = useState<ForecastRequest | null>(null);

  async function handleSubmit(req: ForecastRequest) {
    setLoading(true);
    setError(null);
    setLastRequest(req);
    try {
      const data = await fetchForecast(req);
      setResult(data);
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ??
        err?.message ??
        "Erreur lors de la prévision. Vérifiez que l'API est démarrée.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-100 to-blue-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center text-white font-bold text-lg">
            IF
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-800 leading-tight">ImmoForecast TN</h1>
            <p className="text-xs text-slate-500">Prévision de prix immobiliers tunisiens · 2 ans</p>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-6xl mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6 items-start">
        {/* Left column : form */}
        <div className="space-y-4">
          <ForecastForm onSubmit={handleSubmit} loading={loading} />

          {/* Info box */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-xs text-blue-700 space-y-1">
            <p className="font-semibold">Comment ça marche ?</p>
            <p>Trois modèles concurrents (Prophet, ARIMA, LSTM) analysent les données du marché immobilier tunisien.</p>
            <p>Le meilleur est sélectionné automatiquement selon le MAPE sur les données de test.</p>
          </div>
        </div>

        {/* Right column : results */}
        <div className="space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
              <strong>Erreur :</strong> {error}
            </div>
          )}

          {loading && (
            <div className="bg-white rounded-2xl shadow-md p-12 flex flex-col items-center gap-4">
              <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
              <p className="text-slate-500 text-sm">Calcul de la prévision en cours…</p>
            </div>
          )}

          {result && !loading && (
            <>
              <ResultCard
                resume={result.resume}
                modele={result.modele_utilise}
                mape={result.mape_test}
                zone={result.zone}
                typeBien={result.type_bien}
                prixActuel={lastRequest!.prix_estime_actuel}
              />
              <ForecastChart
                points={result.points}
                prixActuel={lastRequest!.prix_estime_actuel}
              />
            </>
          )}

          {!result && !loading && !error && (
            <div className="bg-white rounded-2xl shadow-md p-12 flex flex-col items-center gap-3 text-slate-400">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-14 h-14 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 3v18h18M9 17l4-8 4 4 2-6" />
              </svg>
              <p className="text-sm">Remplissez le formulaire et cliquez sur <strong>Prévoir l'évolution</strong></p>
            </div>
          )}
        </div>
      </main>

      <footer className="text-center py-6 text-xs text-slate-400">
        NeuroNova · Esprit PI 4DS10 2025-2026 · Données immobilières tunisiennes
      </footer>
    </div>
  );
}
