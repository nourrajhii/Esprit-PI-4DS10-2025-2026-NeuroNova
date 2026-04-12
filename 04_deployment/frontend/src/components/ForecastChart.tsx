import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  ComposedChart,
  ReferenceLine,
} from "recharts";
import type { ForecastPoint } from "../services/api.service";

interface Props {
  points: ForecastPoint[];
  prixActuel: number;
}

interface ChartPoint {
  date: string;
  label: string;
  prix: number;
  ic_bas: number | undefined;
  ic_haut: number | undefined;
  isToday: boolean;
}

const FMT = new Intl.NumberFormat("fr-TN", { maximumFractionDigits: 0 });

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("fr-FR", { month: "short", year: "2-digit" });
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload as ChartPoint;
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-lg text-sm">
      <p className="font-semibold text-slate-700 mb-1">{label}</p>
      <p className="text-blue-600">
        Prix prédit : <strong>{FMT.format(d.prix)} TND/m²</strong>
      </p>
      {d.ic_bas !== undefined && d.ic_haut !== undefined && (
        <p className="text-slate-400 text-xs mt-1">
          IC 90% : [{FMT.format(d.ic_bas)} – {FMT.format(d.ic_haut)}]
        </p>
      )}
    </div>
  );
}

export default function ForecastChart({ points, prixActuel }: Props) {
  const today = new Date().toISOString().slice(0, 7);

  // Ajouter le point "aujourd'hui"
  const todayPoint: ChartPoint = {
    date: today + "-01",
    label: "Aujourd'hui",
    prix: prixActuel,
    ic_bas: undefined,
    ic_haut: undefined,
    isToday: true,
  };

  const data: ChartPoint[] = [
    todayPoint,
    ...points.map((p) => ({
      date: p.date,
      label: formatDate(p.date),
      prix: p.prix_predit,
      ic_bas: p.ic_bas ?? undefined,
      ic_haut: p.ic_haut ?? undefined,
      isToday: false,
    })),
  ];

  // Sous-ensemble pour l'axe X (ne pas afficher trop de labels)
  const step = Math.max(1, Math.floor(data.length / 8));

  const todayLabel = formatDate(today + "-01");

  return (
    <div className="bg-white rounded-2xl shadow-md p-6">
      <h2 className="text-xl font-semibold text-slate-800 mb-4">
        Évolution prévue du prix au m²
      </h2>
      <ResponsiveContainer width="100%" height={360}>
        <ComposedChart data={data} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
          <defs>
            <linearGradient id="icGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.12} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            interval={step - 1}
          />
          <YAxis
            tickFormatter={(v) => FMT.format(v)}
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            width={72}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: 12 }} />

          {/* Zone IC 90% */}
          <Area
            type="monotone"
            dataKey="ic_haut"
            stroke="none"
            fill="url(#icGradient)"
            name="IC 90% haut"
            legendType="none"
            connectNulls
          />
          <Area
            type="monotone"
            dataKey="ic_bas"
            stroke="none"
            fill="#ffffff"
            name="IC 90% bas"
            legendType="none"
            connectNulls
          />

          {/* Ligne de prévision */}
          <Line
            type="monotone"
            dataKey="prix"
            stroke="#2563eb"
            strokeWidth={2.5}
            dot={(props: any) =>
              props.payload.isToday ? (
                <circle
                  key={props.key}
                  cx={props.cx}
                  cy={props.cy}
                  r={6}
                  fill="#f59e0b"
                  stroke="#fff"
                  strokeWidth={2}
                />
              ) : (
                <circle key={props.key} cx={props.cx} cy={props.cy} r={0} />
              )
            }
            activeDot={{ r: 5 }}
            name="Prix prédit (TND/m²)"
            connectNulls
          />

          {/* Ligne verticale "aujourd'hui" */}
          <ReferenceLine x={todayLabel} stroke="#f59e0b" strokeDasharray="4 3" label={{ value: "Aujourd'hui", fill: "#f59e0b", fontSize: 11 }} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
