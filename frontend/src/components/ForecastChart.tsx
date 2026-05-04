'use client'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'

interface ForecastPoint { month: string; price_per_m2_tnd: number; demand_index: number }

export default function ForecastChart({ data, governorat }: { data: ForecastPoint[]; governorat?: string }) {
  return (
    <div className="w-full">
      {governorat && <h3 className="text-sm font-semibold text-slate-700 mb-3">Prévisions 12 mois — {governorat}</h3>}
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <defs>
            <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0284c7" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#0284c7" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="demandGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#64748b' }} />
          <YAxis yAxisId="price" tick={{ fontSize: 11, fill: '#64748b' }} unit=" TND" width={70} />
          <YAxis yAxisId="demand" orientation="right" tick={{ fontSize: 11, fill: '#64748b' }} domain={[0, 100]} />
          <Tooltip
            formatter={(value: number, name: string) =>
              name === 'Prix/m²' ? [`${value.toLocaleString()} TND`, name] : [value, name]
            }
          />
          <Legend />
          <Area yAxisId="price" type="monotone" dataKey="price_per_m2_tnd" stroke="#0284c7" fill="url(#priceGrad)" name="Prix/m²" />
          <Area yAxisId="demand" type="monotone" dataKey="demand_index" stroke="#10b981" fill="url(#demandGrad)" name="Demande" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
