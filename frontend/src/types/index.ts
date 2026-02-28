export type FindingTier = 'auto_verified' | 'needs_review' | 'flagged'

export type DocumentStatus =
  | 'uploading'
  | 'classifying'
  | 'classified'
  | 'needs_classification'
  | 'extracting'
  | 'extracted'
  | 'error'

export interface TaxDocument {
  id: string
  session_id: string
  filename: string
  doc_type: string | null
  classification_confidence: number | null
  status: DocumentStatus
  tax_year: number | null
  created_at: string
}

export interface Finding {
  id: string
  session_id: string
  title: string
  description: string
  tier: FindingTier
  confidence: number
  category: string
  source_document_id: string | null
  action_suggestion: string | null
  why_it_matters: string | null
  reviewed: boolean
  source: 'rule_engine' | 'llm'
  created_at: string
}

export interface Report {
  id: string
  session_id: string
  summary: Record<string, unknown>
  total_income: number | null
  total_tax_deducted: number | null
  document_count: number
  findings_auto_verified: number
  findings_needs_review: number
  findings_flagged: number
  findings: Finding[]
  documents: TaxDocument[]
  created_at: string
}

export interface UploadResponse {
  session_id: string
  documents: TaxDocument[]
}

export interface PipelineEvent {
  stage: 'extracting' | 'analyzing' | 'reporting' | 'complete'
  substage?: 'rule_engine' | 'llm_patterns'
  document?: string
  progress?: number
  total?: number
  report_id?: string
}
