import { useState, useCallback } from 'react'
import api from '../lib/api'
import type { Finding, PipelineEvent, Report, TaxDocument, UploadResponse } from '../types'
import { supabase } from '../lib/supabase'

export function useAnalysis() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [documents, setDocuments] = useState<TaxDocument[]>([])
  const [report, setReport] = useState<Report | null>(null)
  const [pipelineEvents, setPipelineEvents] = useState<PipelineEvent[]>([])
  const [currentStage, setCurrentStage] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const uploadFiles = useCallback(async (files: File[]) => {
    setUploading(true)
    setError(null)

    try {
      const formData = new FormData()
      files.forEach((file) => formData.append('files', file))

      const { data } = await api.post<UploadResponse>('/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      setSessionId(data.session_id)
      setDocuments(data.documents)
      return data
    } catch (err: any) {
      const message = err.response?.data?.detail || err.message || 'Upload failed'
      setError(message)
      throw err
    } finally {
      setUploading(false)
    }
  }, [])

  const correctClassification = useCallback(async (documentId: string, docType: string) => {
    try {
      await api.put(`/api/documents/${documentId}/classify`, null, {
        params: { doc_type: docType },
      })
      setDocuments((prev) =>
        prev.map((d) =>
          d.id === documentId
            ? { ...d, doc_type: docType, classification_confidence: 1.0, status: 'classified' as const }
            : d
        )
      )
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Classification update failed')
    }
  }, [])

  const fetchReport = useCallback(async () => {
    if (!sessionId) return
    try {
      const { data } = await api.get<Report>(`/api/sessions/${sessionId}/report`)
      setReport(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch report')
    }
  }, [sessionId])

  const startAnalysis = useCallback(async () => {
    if (!sessionId) return

    setAnalyzing(true)
    setError(null)
    setPipelineEvents([])
    setCurrentStage('extracting')

    try {
      const { data: { session } } = await supabase.auth.getSession()
      const token = session?.access_token

      const baseUrl = import.meta.env.VITE_API_URL || ''
      const response = await fetch(`${baseUrl}/api/sessions/${sessionId}/analyze`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        throw new Error(`Analysis failed: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) throw new Error('No response body')

      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event: PipelineEvent = JSON.parse(line.slice(6))
              setPipelineEvents((prev) => [...prev, event])
              setCurrentStage(event.stage)

              if (event.stage === 'complete' && event.report_id) {
                await fetchReport()
              }
            } catch {
              // skip malformed events
            }
          }
        }
      }
    } catch (err: any) {
      setError(err.message || 'Analysis failed')
    } finally {
      setAnalyzing(false)
      setCurrentStage(null)
    }
  }, [sessionId, fetchReport])

  const markFindingReviewed = useCallback(async (findingId: string, reviewed: boolean) => {
    try {
      const { data } = await api.patch<Finding>(`/api/findings/${findingId}`, { reviewed })
      setReport((prev) => {
        if (!prev) return prev
        return {
          ...prev,
          findings: prev.findings.map((f) => (f.id === findingId ? data : f)),
        }
      })
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update finding')
    }
  }, [])

  const reset = useCallback(() => {
    setSessionId(null)
    setDocuments([])
    setReport(null)
    setPipelineEvents([])
    setCurrentStage(null)
    setError(null)
  }, [])

  return {
    sessionId,
    documents,
    report,
    pipelineEvents,
    currentStage,
    uploading,
    analyzing,
    error,
    uploadFiles,
    correctClassification,
    startAnalysis,
    fetchReport,
    markFindingReviewed,
    reset,
  }
}
