'use client'
import {
  RadarChart as ReRadar, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip,
} from 'recharts'

interface RadarData { axis: string; value: number }

export default function RadarChart({ data, title }: { data: RadarData[]; title?: string }) {
  return (
    <div className="w-full">
      {title && <h3 className="text-sm font-semibold text-slate-700 mb-2 text-center">{title}</h3>}
      <ResponsiveContainer width="100%" height={280}>
        <ReRadar data={data} cx="50%" cy="50%" outerRadius="75%">
          <PolarGrid />
          <PolarAngleAxis dataKey="axis" tick={{ fill: '#64748b', fontSize: 12 }} />
          <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 10 }} />
          <Radar
            name="Score"
            dataKey="value"
            stroke="#0284c7"
            fill="#0284c7"
            fillOpacity={0.25}
          />
          <Tooltip />
        </ReRadar>
      </ResponsiveContainer>
    </div>
  )
}
