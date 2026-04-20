import { useState } from "react";
import ForecastForm from "./components/ForecastForm";
import ForecastChart from "./components/ForecastChart";
import AgentReport from "./components/AgentReport";
import {
  analyzeVente,
  analyzeLocation,
  type VenteRequest,
  type LocationRequest,
  type AgentResponse,
} from "./services/api.service";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleVente(req: VenteRequest) {
    setLoading(true);
    setError(null);
    try {
      setResult(await analyzeVente(req));
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ??
        err?.message ??
        "Erreur lors de l'analyse. Vérifiez que l'API est démarrée."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleLocation(req: LocationRequest) {
    setLoading(true);
    setError(null);
    try {
      setResult(await analyzeLocation(req));
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ??
        err?.message ??
        "Erreur lors de l'analyse. Vérifiez que l'API est démarrée."
      );
    } finally {
      setLoading(false);
    }
  }

  const unite = result?.mode === "location" ? "TND/mois" : "TND/m²";

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
            <p className="text-xs text-slate-500">Agent IA · Analyse de marché immobilier tunisien · 24 gouvernorats</p>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-6xl mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6 items-start">

        {/* Colonne gauche : formulaire */}
        <div className="space-y-4">
          <ForecastForm
            onSubmitVente={handleVente}
            onSubmitLocation={handleLocation}
            loading={loading}
          />

          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-xs text-blue-700 space-y-1">
            <p className="font-semibold">Comment fonctionne l'agent ?</p>
            <p>
              L'agent analyse le profil de marché du gouvernorat sélectionné :
              tension offre/demande, historique de croissance, saisonnalité,
              et facteurs économiques locaux.
            </p>
            <p>
              Il positionne votre bien par rapport aux moyennes du marché
              et génère une prévision sur 4 horizons (6, 12, 18, 24 mois)
              avec recommandation contextuelle.
            </p>
          </div>
        </div>

        {/* Colonne droite : résultats */}
        <div className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
              <strong>Erreur :</strong> {error}
            </div>
          )}

          {loading && (
            <div className="bg-white rounded-2xl shadow-md p-12 flex flex-col items-center gap-4">
              <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
              <p className="text-slate-500 text-sm">L'agent analyse le marché…</p>
            </div>
          )}

          {result && !loading && (
            <>
              <AgentReport result={result} />
              <ForecastChart
                points={result.points}
                valeurActuelle={result.valeur_saisie}
                unite={unite}
                titre={
                  result.mode === "vente"
                    ? `Évolution du prix au m² — ${result.gouvernorat}`
                    : `Évolution du loyer ${result.composition} — ${result.gouvernorat}`
                }
              />
            </>
          )}

          {!result && !loading && !error && (
            <div className="bg-white rounded-2xl shadow-md p-12 flex flex-col items-center gap-3 text-slate-400">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-14 h-14 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 3v18h18M9 17l4-8 4 4 2-6" />
              </svg>
              <p className="text-sm text-center">
                Sélectionnez un gouvernorat, un mode <strong>Vente</strong> ou <strong>Location</strong>,
                puis cliquez sur <strong>Lancer l'analyse</strong>.
              </p>
            </div>
          )}
        </div>
      </main>

      <footer className="text-center py-6 text-xs text-slate-400">
        NeuroNova · Esprit PI 4DS10 2025-2026 · Marché immobilier tunisien
      </footer>
    </div>
  );
}
