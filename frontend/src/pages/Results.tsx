import { useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Loader2 } from 'lucide-react'
import Navbar from '../components/Navbar'
import PipelineProgress from '../components/PipelineProgress'
import AnalysisDashboard from '../components/AnalysisDashboard'
import { useAnalysis } from '../hooks/useAnalysis'

export default function Results() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const {
    report,
    pipelineEvents,
    currentStage,
    analyzing,
    error,
    startAnalysis,
    fetchReport,
    markFindingReviewed,
  } = useAnalysis()

  useEffect(() => {
    if (sessionId && !report && !analyzing) {
      // Try to fetch an existing report first
      fetchReport().catch(() => {
        // No report yet — start analysis
        startAnalysis()
      })
    }
  }, [sessionId, report, analyzing, fetchReport, startAnalysis])

  const latestEvent = pipelineEvents[pipelineEvents.length - 1]
  const substage = latestEvent?.substage

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <main className="max-w-4xl mx-auto px-4 py-8">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-6 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to upload
        </Link>

        <h1 className="text-2xl font-bold text-gray-900 mb-2">Analysis Results</h1>
        <p className="text-sm text-gray-500 mb-6">
          {report
            ? `Analyzed ${report.document_count} document${report.document_count !== 1 ? 's' : ''} with ${report.findings.length} finding${report.findings.length !== 1 ? 's' : ''}.`
            : analyzing
              ? 'Processing your documents...'
              : 'Preparing analysis...'}
        </p>

        {/* Error */}
        {error && (
          <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Pipeline progress (while analyzing) */}
        {analyzing && (
          <div className="mb-8">
            <PipelineProgress currentStage={currentStage} substage={substage} />

            {latestEvent?.stage === 'extracting' && (
              <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Extracting data from {latestEvent.document}
                {latestEvent.progress && latestEvent.total && (
                  <span className="text-gray-400">
                    ({latestEvent.progress}/{latestEvent.total})
                  </span>
                )}
              </div>
            )}
          </div>
        )}

        {/* Report dashboard */}
        {report && (
          <AnalysisDashboard report={report} onToggleReviewed={markFindingReviewed} />
        )}

        {/* Loading state when no report and not analyzing */}
        {!report && !analyzing && !error && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        )}
      </main>
    </div>
  )
}
