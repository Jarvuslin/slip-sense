import { CheckCircle, AlertTriangle, AlertOctagon, Cpu, Brain, Eye } from 'lucide-react'
import type { Finding } from '../types'
import ConfidenceBadge from './ConfidenceBadge'

interface FindingCardProps {
  finding: Finding
  onToggleReviewed?: (findingId: string, reviewed: boolean) => void
}

const tierConfig = {
  auto_verified: {
    icon: CheckCircle,
    iconColor: 'text-emerald-500',
    borderColor: 'border-l-emerald-500',
  },
  needs_review: {
    icon: AlertTriangle,
    iconColor: 'text-amber-500',
    borderColor: 'border-l-amber-500',
  },
  flagged: {
    icon: AlertOctagon,
    iconColor: 'text-red-500',
    borderColor: 'border-l-red-500',
  },
}

export default function FindingCard({ finding, onToggleReviewed }: FindingCardProps) {
  const config = tierConfig[finding.tier]
  const TierIcon = config.icon

  return (
    <div
      className={`bg-white rounded-lg border border-gray-200 border-l-4 ${config.borderColor} p-4 transition-opacity ${
        finding.reviewed ? 'opacity-60' : ''
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1">
          <TierIcon className={`h-5 w-5 mt-0.5 shrink-0 ${config.iconColor}`} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-sm font-semibold text-gray-900">{finding.title}</h4>
              <ConfidenceBadge confidence={finding.confidence} />
              {finding.source === 'llm' ? (
                <span className="inline-flex items-center gap-1 text-xs text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded">
                  <Brain className="h-3 w-3" /> AI
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-xs text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">
                  <Cpu className="h-3 w-3" /> Rule
                </span>
              )}
            </div>
            <p className="mt-1.5 text-sm text-gray-600 leading-relaxed">{finding.description}</p>

            {finding.why_it_matters && (
              <p className="mt-2 text-xs text-gray-500">
                <span className="font-medium">Why it matters:</span> {finding.why_it_matters}
              </p>
            )}

            {finding.action_suggestion && (
              <div className="mt-2 flex items-start gap-1.5 text-xs text-indigo-700 bg-indigo-50 rounded px-2 py-1.5">
                <Eye className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                <span>{finding.action_suggestion}</span>
              </div>
            )}
          </div>
        </div>

        <button
          onClick={() => onToggleReviewed?.(finding.id, !finding.reviewed)}
          className={`shrink-0 text-xs px-2.5 py-1 rounded-full border transition-colors ${
            finding.reviewed
              ? 'border-emerald-300 bg-emerald-50 text-emerald-700'
              : 'border-gray-300 bg-white text-gray-500 hover:bg-gray-50'
          }`}
        >
          {finding.reviewed ? 'Reviewed' : 'Mark reviewed'}
        </button>
      </div>
    </div>
  )
}
