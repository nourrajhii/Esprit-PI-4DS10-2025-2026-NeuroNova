import { cn } from '@/lib/utils'

interface Props {
  verdict: 'BUY' | 'HOLD' | 'AVOID' | string
  score?: number
  size?: 'sm' | 'md' | 'lg'
}

const LABELS: Record<string, string> = { BUY: 'ACHETER', HOLD: 'ATTENDRE', AVOID: 'ÉVITER' }

export default function InvestmentBadge({ verdict, score, size = 'md' }: Props) {
  const sizeClass = size === 'sm' ? 'text-xs px-2 py-0.5' : size === 'lg' ? 'text-base px-4 py-2' : 'text-sm px-3 py-1'
  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-full font-bold', sizeClass, `verdict-${verdict}`)}>
      {verdict === 'BUY' ? '✅' : verdict === 'HOLD' ? '⏸️' : '❌'}
      {LABELS[verdict] || verdict}
      {score != null && <span className="opacity-70">({score}/100)</span>}
    </span>
  )
}
