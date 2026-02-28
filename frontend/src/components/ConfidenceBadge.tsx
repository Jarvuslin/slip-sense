interface ConfidenceBadgeProps {
  confidence: number
  size?: 'sm' | 'md'
}

export default function ConfidenceBadge({ confidence, size = 'sm' }: ConfidenceBadgeProps) {
  const pct = Math.round(confidence * 100)
  const isSmall = size === 'sm'

  let colorClasses: string
  if (confidence >= 0.9) {
    colorClasses = 'bg-emerald-100 text-emerald-800'
  } else if (confidence >= 0.6) {
    colorClasses = 'bg-amber-100 text-amber-800'
  } else {
    colorClasses = 'bg-red-100 text-red-800'
  }

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full ${colorClasses} ${
        isSmall ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm'
      }`}
    >
      {pct}%
    </span>
  )
}
