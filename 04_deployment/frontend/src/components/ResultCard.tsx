import type { ForecastResume } from "../services/api.service";

interface Props {
  resume: ForecastResume;
  modele: string;
  mape: number | null;
  zone: string;
  typeBien: string;
  prixActuel: number;
}

const FMT = new Intl.NumberFormat("fr-TN", { maximumFractionDigits: 0 });

function VariationBadge({ pct }: { pct: number }) {
  const isUp = pct >= 0;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${
        isUp
          ? "bg-emerald-100 text-emerald-700"
          : "bg-red-100 text-red-600"
      }`}
    >
      {isUp ? "+" : ""}{pct.toFixed(1)}%
    </span>
  );
}

function TendancePill({ tendance }: { tendance: string }) {
  const cfg: Record<string, { label: string; cls: string }> = {
    hausse: { label: "Tendance haussière", cls: "bg-emerald-50 text-emerald-700 border border-emerald-200" },
    baisse: { label: "Tendance baissière", cls: "bg-red-50 text-red-600 border border-red-200" },
    stable: { label: "Marché stable", cls: "bg-slate-100 text-slate-600 border border-slate-200" },
  };
  const { label, cls } = cfg[tendance] ?? cfg.stable;
  return (
    <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${cls}`}>
      {label}
    </span>
  );
}

export default function ResultCard({ resume, modele, mape, zone, typeBien, prixActuel }: Props) {
  return (
    <div className="bg-white rounded-2xl shadow-md p-6 space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-800">Résultats</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {typeBien.charAt(0).toUpperCase() + typeBien.slice(1)} · {zone}
          </p>
        </div>
        <TendancePill tendance={resume.tendance} />
      </div>

      {/* Prix actuels vs prédits */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl bg-slate-50 p-3 text-center">
          <p className="text-xs text-slate-500 mb-1">Aujourd'hui</p>
          <p className="text-lg font-bold text-slate-800">{FMT.format(prixActuel)}</p>
          <p className="text-xs text-slate-400">TND/m²</p>
        </div>
        <div className="rounded-xl bg-blue-50 p-3 text-center">
          <p className="text-xs text-blue-500 mb-1">Dans 12 mois</p>
          <p className="text-lg font-bold text-blue-700">{FMT.format(resume.prix_j12)}</p>
          <div className="flex justify-center mt-1">
            <VariationBadge pct={resume.variation_pct_12} />
          </div>
        </div>
        <div className="rounded-xl bg-indigo-50 p-3 text-center">
          <p className="text-xs text-indigo-500 mb-1">Dans 24 mois</p>
          <p className="text-lg font-bold text-indigo-700">{FMT.format(resume.prix_j24)}</p>
          <div className="flex justify-center mt-1">
            <VariationBadge pct={resume.variation_pct_24} />
          </div>
        </div>
      </div>

      {/* Métadonnées modèle */}
      <div className="border-t border-slate-100 pt-4 flex flex-wrap gap-4 text-xs text-slate-500">
        <div>
          <span className="font-medium text-slate-700">Modèle :</span>{" "}
          <span className="uppercase font-semibold text-blue-600">{modele}</span>
        </div>
        {mape !== null && mape !== undefined && (
          <div>
            <span className="font-medium text-slate-700">MAPE test :</span>{" "}
            <span className={mape < 10 ? "text-emerald-600 font-semibold" : "text-amber-600 font-semibold"}>
              {mape.toFixed(1)}%
            </span>
          </div>
        )}
        <div className="ml-auto text-slate-400 italic">
          IC 90% affiché sur le graphique
        </div>
      </div>
    </div>
  );
}
