import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, ArrowRight, Loader2 } from 'lucide-react'
import Navbar from '../components/Navbar'
import UploadZone from '../components/UploadZone'
import DocumentList from '../components/DocumentList'
import { useAnalysis } from '../hooks/useAnalysis'

export default function Upload() {
  const navigate = useNavigate()
  const {
    sessionId,
    documents,
    uploading,
    error,
    uploadFiles,
    correctClassification,
  } = useAnalysis()
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])

  const handleFilesSelected = (files: File[]) => {
    setSelectedFiles((prev) => [...prev, ...files])
  }

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return
    const data = await uploadFiles(selectedFiles)
    if (data) {
      setSelectedFiles([])
    }
  }

  const handleAnalyze = () => {
    if (sessionId) {
      navigate(`/results/${sessionId}`)
    }
  }

  const allClassified = documents.length > 0 && documents.every(
    (d) => d.status === 'classified' || d.status === 'extracted'
  )

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <main className="max-w-3xl mx-auto px-4 py-8">
        {/* Disclaimer banner */}
        <div className="mb-6 flex items-start gap-2.5 p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
          <p className="text-xs text-amber-700">
            <strong>Important:</strong> SlipSense.AI is an analysis tool, not tax advice. All findings are
            suggestions for your review. For complex tax situations, consult a qualified tax professional.
          </p>
        </div>

        <h1 className="text-2xl font-bold text-gray-900 mb-2">Upload Tax Documents</h1>
        <p className="text-sm text-gray-500 mb-6">
          Upload your Canadian tax slips (T4, T5, T2202, RRSP receipts) as PDF or images. The system
          will classify, extract, and analyze them for anomalies and missed deductions.
        </p>

        {/* Upload zone */}
        <div className="mb-6">
          <UploadZone
            onFilesSelected={handleFilesSelected}
            disabled={uploading}
          />
        </div>

        {/* Pending files */}
        {selectedFiles.length > 0 && !sessionId && (
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600">
                {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
              </span>
              <button
                onClick={() => setSelectedFiles([])}
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                Clear
              </button>
            </div>
            <ul className="text-sm text-gray-500 space-y-1 mb-4">
              {selectedFiles.map((f, i) => (
                <li key={i} className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-gray-300" />
                  {f.name}
                  <span className="text-xs text-gray-400">({(f.size / 1024).toFixed(0)} KB)</span>
                </li>
              ))}
            </ul>
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="w-full py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center justify-center gap-2 transition-colors"
            >
              {uploading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Uploading & classifying...
                </>
              ) : (
                'Upload & Classify'
              )}
            </button>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Classified documents */}
        {documents.length > 0 && (
          <div className="space-y-4">
            <DocumentList
              documents={documents}
              onCorrectType={correctClassification}
            />

            <button
              onClick={handleAnalyze}
              disabled={!allClassified}
              className="w-full py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
            >
              Analyze Documents
              <ArrowRight className="h-4 w-4" />
            </button>

            {!allClassified && (
              <p className="text-xs text-amber-600 text-center">
                Some documents need manual classification before analysis can begin.
              </p>
            )}
          </div>
        )}

        {/* Supported documents */}
        {documents.length === 0 && selectedFiles.length === 0 && (
          <div className="mt-8">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Supported Documents</h3>
            <div className="grid grid-cols-2 gap-3">
              {[
                { type: 'T4', desc: 'Employment Income', supported: true },
                { type: 'T5', desc: 'Investment Income', supported: true },
                { type: 'T2202', desc: 'Tuition Certificate', supported: true },
                { type: 'RRSP', desc: 'Contribution Receipt', supported: true },
                { type: 'T4A', desc: 'Pension/Other Income', supported: false },
                { type: 'T3', desc: 'Trust Income', supported: false },
              ].map((d) => (
                <div
                  key={d.type}
                  className={`p-3 rounded-lg border ${
                    d.supported
                      ? 'border-gray-200 bg-white'
                      : 'border-dashed border-gray-200 bg-gray-50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-900">{d.type}</span>
                    {!d.supported && (
                      <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                        Coming soon
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{d.desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
