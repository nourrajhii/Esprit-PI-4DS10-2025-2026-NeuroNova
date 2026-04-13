import type { AgentResponse } from "../services/api.service";

interface Props {
  result: AgentResponse;
}

const FMT = new Intl.NumberFormat("fr-TN", { maximumFractionDigits: 0 });

// ── Composants internes ───────────────────────────────────────────────────────

function RisqueBadge({ risque }: { risque: string }) {
  const cfg: Record<string, { cls: string; dot: string }> = {
    Faible:  { cls: "bg-emerald-100 text-emerald-700 border-emerald-200", dot: "bg-emerald-500" },
    Modéré:  { cls: "bg-amber-100 text-amber-700 border-amber-200",       dot: "bg-amber-500"   },
    Élevé:   { cls: "bg-red-100 text-red-600 border-red-200",             dot: "bg-red-500"     },
  };
  const { cls, dot } = cfg[risque] ?? cfg["Modéré"];
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${cls}`}>
      <span className={`w-2 h-2 rounded-full ${dot}`} />
      Risque {risque}
    </span>
  );
}

function TendancePill({ tendance }: { tendance: string }) {
  const cfg: Record<string, { label: string; cls: string }> = {
    hausse: { label: "Tendance haussière", cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
    baisse: { label: "Tendance baissière", cls: "bg-red-50 text-red-600 border-red-200"             },
    stable: { label: "Marché stable",      cls: "bg-slate-100 text-slate-600 border-slate-200"      },
  };
  const { label, cls } = cfg[tendance] ?? cfg.stable;
  return (
    <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium border ${cls}`}>
      {label}
    </span>
  );
}

function VarBadge({ pct }: { pct: number }) {
  const isUp = pct >= 0;
  return (
    <span className={`text-xs font-bold ${isUp ? "text-emerald-600" : "text-red-500"}`}>
      {isUp ? "+" : ""}{pct.toFixed(1)}%
    </span>
  );
}

function PositionnementBar({ diff }: { diff: number }) {
  // -50%..+50% → 0..100%
  const clamped = Math.max(-50, Math.min(50, diff));
  const pct = ((clamped + 50) / 100) * 100;
  const color = diff < -5 ? "bg-sky-500" : diff > 5 ? "bg-amber-500" : "bg-emerald-500";
  return (
    <div className="relative h-3 bg-slate-100 rounded-full overflow-hidden mt-2">
      <div
        className={`absolute top-0 h-full w-1 ${color} rounded-full transition-all duration-700`}
        style={{ left: `calc(${pct}% - 2px)` }}
      />
      <div className="absolute top-0 left-1/2 w-px h-full bg-slate-400 opacity-40" />
    </div>
  );
}

// ── Composant principal ───────────────────────────────────────────────────────

export default function AgentReport({ result }: Props) {
  const {
    mode, gouvernorat, type_bien, composition, superficie,
    valeur_saisie, valeur_totale_actuelle, prix_moyen_marche,
    diff_vs_marche_pct, statut_prix, taux_annuel,
    horizons, tendance, risque, tension,
    analyse_marche, facteurs, recommandation,
  } = result;

  const unite = mode === "vente" ? "TND/m²" : "TND/mois";
  const labelBien = mode === "vente"
    ? `${type_bien ? type_bien.charAt(0).toUpperCase() + type_bien.slice(1) : ""} · ${gouvernorat}`
    : `${composition} · ${gouvernorat}`;

  const statutColor =
    statut_prix.includes("sous") ? "text-sky-600" :
    statut_prix.includes("surévalué") ? "text-amber-600" :
    "text-emerald-600";

  const HORIZONS: Array<{ key: "6" | "12" | "18" | "24"; label: string; bg: string; text: string }> = [
    { key: "6",  label: "+6 mois",  bg: "bg-sky-50",    text: "text-sky-700"    },
    { key: "12", label: "+12 mois", bg: "bg-blue-50",   text: "text-blue-700"   },
    { key: "18", label: "+18 mois", bg: "bg-violet-50", text: "text-violet-700" },
    { key: "24", label: "+24 mois", bg: "bg-indigo-50", text: "text-indigo-700" },
  ];

  return (
    <div className="space-y-4">

      {/* ── 1. En-tête résumé ── */}
      <div className="bg-white rounded-2xl shadow-md p-6">
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-xl font-semibold text-slate-800">Rapport d'analyse</h2>
            <p className="text-sm text-slate-500 mt-0.5">{labelBien}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <TendancePill tendance={tendance} />
            <RisqueBadge risque={risque} />
          </div>
        </div>

        {/* Métadonnées */}
        <div className="mt-4 flex flex-wrap gap-4 text-xs text-slate-500">
          <div>
            <span className="font-medium text-slate-700">Tension :</span>{" "}
            <span className="font-semibold text-blue-600 capitalize">{tension}</span>
          </div>
          <div>
            <span className="font-medium text-slate-700">Croissance annuelle estimée :</span>{" "}
            <span className="font-semibold text-emerald-600">{taux_annuel.toFixed(1)}%/an</span>
          </div>
          {mode === "vente" && superficie && (
            <div>
              <span className="font-medium text-slate-700">Valeur totale actuelle :</span>{" "}
              <span className="font-semibold text-slate-800">
                {FMT.format(valeur_totale_actuelle ?? 0)} TND
              </span>
            </div>
          )}
        </div>
      </div>

      {/* ── 2. Positionnement marché ── */}
      <div className="bg-white rounded-2xl shadow-md p-6">
        <h3 className="text-base font-semibold text-slate-800 mb-4">Positionnement marché</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-xl bg-slate-50 p-4 text-center">
            <p className="text-xs text-slate-500 mb-1">
              {mode === "vente" ? "Votre prix/m²" : "Votre loyer"}
            </p>
            <p className="text-2xl font-bold text-slate-800">{FMT.format(valeur_saisie)}</p>
            <p className="text-xs text-slate-400 mt-0.5">{unite}</p>
          </div>
          <div className="rounded-xl bg-blue-50 p-4 text-center">
            <p className="text-xs text-blue-500 mb-1">
              Moyenne {gouvernorat}
            </p>
            <p className="text-2xl font-bold text-blue-700">{FMT.format(prix_moyen_marche)}</p>
            <p className="text-xs text-blue-400 mt-0.5">{unite}</p>
          </div>
        </div>

        <div className="mt-4 text-center">
          <span className={`text-sm font-semibold capitalize ${statutColor}`}>
            {statut_prix}
          </span>
          <span className="text-sm text-slate-500 ml-2">
            ({diff_vs_marche_pct > 0 ? "+" : ""}{diff_vs_marche_pct.toFixed(1)}% vs marché)
          </span>
          <PositionnementBar diff={diff_vs_marche_pct} />
          <div className="flex justify-between text-xs text-slate-400 mt-1">
            <span>−50%</span>
            <span>Moyenne marché</span>
            <span>+50%</span>
          </div>
        </div>
      </div>

      {/* ── 3. Prévisions 4 horizons ── */}
      <div className="bg-white rounded-2xl shadow-md p-6">
        <h3 className="text-base font-semibold text-slate-800 mb-4">Prévisions de prix</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {HORIZONS.map(({ key, label, bg, text }) => {
            const h = horizons[key];
            return (
              <div key={key} className={`rounded-xl ${bg} p-4 text-center`}>
                <p className={`text-xs font-medium mb-1 ${text}`}>{label}</p>
                <p className={`text-xl font-bold ${text}`}>{FMT.format(h.valeur)}</p>
                <p className="text-xs text-slate-400 mt-0.5">{unite}</p>
                <div className="mt-2">
                  <VarBadge pct={h.variation_pct} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── 4. Analyse de marché ── */}
      <div className="bg-white rounded-2xl shadow-md p-6">
        <h3 className="text-base font-semibold text-slate-800 mb-3">Analyse du marché local</h3>
        <p className="text-sm text-slate-600 leading-relaxed">{analyse_marche}</p>

        <div className="mt-4">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Facteurs clés</p>
          <div className="flex flex-wrap gap-2">
            {facteurs.map((f, i) => (
              <span
                key={i}
                className="inline-block px-3 py-1 bg-blue-50 text-blue-700 text-xs rounded-full border border-blue-200"
              >
                {f}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* ── 5. Recommandation agent ── */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl shadow-md p-6 text-white">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-7 h-7 rounded-lg bg-white/20 flex items-center justify-center text-sm font-bold">
            IA
          </div>
          <h3 className="text-base font-semibold">Recommandation de l'agent</h3>
        </div>
        <p className="text-sm leading-relaxed text-blue-50">{recommandation}</p>
      </div>

    </div>
  );
}
