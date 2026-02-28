import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText } from 'lucide-react'

interface UploadZoneProps {
  onFilesSelected: (files: File[]) => void
  disabled?: boolean
}

export default function UploadZone({ onFilesSelected, disabled }: UploadZoneProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (!disabled) onFilesSelected(acceptedFiles)
    },
    [onFilesSelected, disabled]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
    },
    disabled,
    multiple: true,
  })

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer ${
        disabled
          ? 'border-gray-200 bg-gray-50 cursor-not-allowed'
          : isDragActive
            ? 'border-indigo-500 bg-indigo-50'
            : 'border-gray-300 hover:border-indigo-400 hover:bg-gray-50'
      }`}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-3">
        <div
          className={`w-14 h-14 rounded-full flex items-center justify-center ${
            isDragActive ? 'bg-indigo-100' : 'bg-gray-100'
          }`}
        >
          {isDragActive ? (
            <FileText className="h-7 w-7 text-indigo-600" />
          ) : (
            <Upload className="h-7 w-7 text-gray-400" />
          )}
        </div>
        {isDragActive ? (
          <p className="text-indigo-600 font-medium">Drop your tax documents here</p>
        ) : (
          <>
            <p className="text-gray-700 font-medium">
              Drag & drop your tax documents here
            </p>
            <p className="text-sm text-gray-500">
              or click to browse. Supports PDF, PNG, JPG.
            </p>
          </>
        )}
      </div>
    </div>
  )
}
