import { useState } from 'react'
import { ChevronDown, ChevronRight, CheckCircle, AlertTriangle, AlertOctagon, DollarSign, FileText, BarChart3 } from 'lucide-react'
import type { Report, Finding } from '../types'
import FindingCard from './FindingCard'

interface AnalysisDashboardProps {
  report: Report
  onToggleReviewed: (findingId: string, reviewed: boolean) => void
}

export default function AnalysisDashboard({ report, onToggleReviewed }: AnalysisDashboardProps) {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    auto_verified: false,
    needs_review: true,
    flagged: true,
  })

  const toggle = (section: string) =>
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }))

  const autoVerified = report.findings.filter((f) => f.tier === 'auto_verified')
  const needsReview = report.findings.filter((f) => f.tier === 'needs_review')
  const flagged = report.findings.filter((f) => f.tier === 'flagged')

  const formatMoney = (val: number | null) =>
    val != null ? `$${val.toLocaleString('en-CA', { minimumFractionDigits: 2 })}` : '—'

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          icon={<FileText className="h-5 w-5 text-indigo-500" />}
          label="Documents"
          value={report.document_count.toString()}
        />
        <SummaryCard
          icon={<DollarSign className="h-5 w-5 text-emerald-500" />}
          label="Total Income"
          value={formatMoney(report.total_income)}
        />
        <SummaryCard
          icon={<DollarSign className="h-5 w-5 text-blue-500" />}
          label="Tax Deducted"
          value={formatMoney(report.total_tax_deducted)}
        />
        <SummaryCard
          icon={<BarChart3 className="h-5 w-5 text-amber-500" />}
          label="Findings"
          value={report.findings.length.toString()}
        />
      </div>

      {/* Finding tier breakdowns */}
      <div className="flex gap-3">
        <span className="inline-flex items-center gap-1.5 text-sm">
          <CheckCircle className="h-4 w-4 text-emerald-500" /> {report.findings_auto_verified} verified
        </span>
        <span className="inline-flex items-center gap-1.5 text-sm">
          <AlertTriangle className="h-4 w-4 text-amber-500" /> {report.findings_needs_review} to review
        </span>
        <span className="inline-flex items-center gap-1.5 text-sm">
          <AlertOctagon className="h-4 w-4 text-red-500" /> {report.findings_flagged} flagged
        </span>
      </div>

      {/* Flagged section */}
      {flagged.length > 0 && (
        <FindingsSection
          title="Flagged"
          subtitle="Potential issues requiring your attention"
          icon={<AlertOctagon className="h-5 w-5 text-red-500" />}
          findings={flagged}
          expanded={expandedSections.flagged}
          onToggle={() => toggle('flagged')}
          onToggleReviewed={onToggleReviewed}
          headerColor="bg-red-50 border-red-200"
        />
      )}

      {/* Needs Review section */}
      {needsReview.length > 0 && (
        <FindingsSection
          title="Needs Review"
          subtitle="Probably correct but worth double-checking"
          icon={<AlertTriangle className="h-5 w-5 text-amber-500" />}
          findings={needsReview}
          expanded={expandedSections.needs_review}
          onToggle={() => toggle('needs_review')}
          onToggleReviewed={onToggleReviewed}
          headerColor="bg-amber-50 border-amber-200"
        />
      )}

      {/* Auto Verified section */}
      {autoVerified.length > 0 && (
        <FindingsSection
          title="Auto-Verified"
          subtitle="High confidence — no action needed"
          icon={<CheckCircle className="h-5 w-5 text-emerald-500" />}
          findings={autoVerified}
          expanded={expandedSections.auto_verified}
          onToggle={() => toggle('auto_verified')}
          onToggleReviewed={onToggleReviewed}
          headerColor="bg-emerald-50 border-emerald-200"
        />
      )}

      {/* Disclaimer */}
      <div className="text-xs text-gray-400 text-center pt-4 border-t border-gray-100">
        This is an analysis tool, not tax advice. All findings are suggestions — you make the final
        decisions. For complex tax situations, consult a qualified tax professional.
      </div>
    </div>
  )
}

function SummaryCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: string
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs text-gray-500 font-medium">{label}</span>
      </div>
      <p className="text-lg font-semibold text-gray-900">{value}</p>
    </div>
  )
}

function FindingsSection({
  title,
  subtitle,
  icon,
  findings,
  expanded,
  onToggle,
  onToggleReviewed,
  headerColor,
}: {
  title: string
  subtitle: string
  icon: React.ReactNode
  findings: Finding[]
  expanded: boolean
  onToggle: () => void
  onToggleReviewed: (findingId: string, reviewed: boolean) => void
  headerColor: string
}) {
  return (
    <div className="rounded-xl border border-gray-200 overflow-hidden">
      <button
        onClick={onToggle}
        className={`w-full px-4 py-3 flex items-center justify-between ${headerColor} border-b`}
      >
        <div className="flex items-center gap-2">
          {icon}
          <div className="text-left">
            <span className="text-sm font-semibold text-gray-900">
              {title} ({findings.length})
            </span>
            <p className="text-xs text-gray-500">{subtitle}</p>
          </div>
        </div>
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-gray-400" />
        ) : (
          <ChevronRight className="h-4 w-4 text-gray-400" />
        )}
      </button>
      {expanded && (
        <div className="p-4 space-y-3 bg-gray-50">
          {findings.map((f) => (
            <FindingCard key={f.id} finding={f} onToggleReviewed={onToggleReviewed} />
          ))}
        </div>
      )}
    </div>
  )
}
