import { Check, FileSearch, Brain, FileText } from 'lucide-react'

const STAGES = [
  { key: 'extracting', label: 'Extracting Data', icon: FileSearch },
  { key: 'analyzing', label: 'Analyzing', icon: Brain },
  { key: 'reporting', label: 'Generating Report', icon: FileText },
  { key: 'complete', label: 'Complete', icon: Check },
] as const

interface PipelineProgressProps {
  currentStage: string | null
  substage?: string
}

export default function PipelineProgress({ currentStage, substage }: PipelineProgressProps) {
  const currentIndex = STAGES.findIndex((s) => s.key === currentStage)

  return (
    <div className="w-full py-6">
      <div className="flex items-center justify-between">
        {STAGES.map((stage, index) => {
          const Icon = stage.icon
          const isComplete = index < currentIndex || currentStage === 'complete'
          const isCurrent = index === currentIndex && currentStage !== 'complete'

          return (
            <div key={stage.key} className="flex flex-1 items-center">
              <div className="flex flex-col items-center flex-1">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300 ${
                    isComplete
                      ? 'bg-emerald-500 text-white'
                      : isCurrent
                        ? 'bg-indigo-600 text-white animate-pulse'
                        : 'bg-gray-200 text-gray-400'
                  }`}
                >
                  {isComplete ? <Check className="h-5 w-5" /> : <Icon className="h-5 w-5" />}
                </div>
                <span
                  className={`mt-2 text-xs font-medium ${
                    isComplete || isCurrent ? 'text-gray-900' : 'text-gray-400'
                  }`}
                >
                  {stage.label}
                </span>
                {isCurrent && substage && (
                  <span className="text-xs text-indigo-600 mt-0.5">
                    {substage === 'rule_engine' ? 'Rule checks...' : 'AI patterns...'}
                  </span>
                )}
              </div>
              {index < STAGES.length - 1 && (
                <div
                  className={`h-0.5 flex-1 mx-2 transition-colors duration-300 ${
                    index < currentIndex ? 'bg-emerald-500' : 'bg-gray-200'
                  }`}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
