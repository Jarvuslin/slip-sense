import { FileText, AlertCircle, Check } from 'lucide-react'
import type { TaxDocument } from '../types'
import ConfidenceBadge from './ConfidenceBadge'

const DOC_TYPE_LABELS: Record<string, string> = {
  T4: 'T4 — Employment Income',
  T5: 'T5 — Investment Income',
  T2202: 'T2202 — Tuition',
  RRSP: 'RRSP Contribution',
  T4A: 'T4A — Pension/Other',
  T4E: 'T4E — EI Benefits',
  T3: 'T3 — Trust Income',
  T5007: 'T5007 — Benefits',
  DONATION: 'Charitable Donation',
  UNKNOWN: 'Unknown Document',
}

const VALID_TYPES = ['T4', 'T5', 'T2202', 'RRSP', 'T4A', 'T4E', 'T3', 'T5007', 'DONATION']

interface DocumentListProps {
  documents: TaxDocument[]
  onCorrectType?: (documentId: string, newType: string) => void
}

export default function DocumentList({ documents, onCorrectType }: DocumentListProps) {
  if (documents.length === 0) return null

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700">
          Uploaded Documents ({documents.length})
        </h3>
      </div>
      <ul className="divide-y divide-gray-100">
        {documents.map((doc) => (
          <li key={doc.id} className="px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileText className="h-5 w-5 text-gray-400 shrink-0" />
              <div>
                <p className="text-sm font-medium text-gray-900">{doc.filename}</p>
                <p className="text-xs text-gray-500">
                  {DOC_TYPE_LABELS[doc.doc_type || 'UNKNOWN'] || doc.doc_type}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {doc.classification_confidence != null && (
                <ConfidenceBadge confidence={doc.classification_confidence} />
              )}

              {doc.status === 'needs_classification' && (
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-amber-500" />
                  <select
                    className="text-xs border border-gray-300 rounded px-2 py-1 focus:ring-indigo-500 focus:border-indigo-500"
                    defaultValue=""
                    onChange={(e) => onCorrectType?.(doc.id, e.target.value)}
                  >
                    <option value="" disabled>
                      Correct type...
                    </option>
                    {VALID_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {doc.status === 'classified' && (
                <Check className="h-4 w-4 text-emerald-500" />
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
