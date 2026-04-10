import { useState } from 'react'
import FileUploadZone from '../components/organize/FileUploadZone'
import ClassificationPreview from '../components/organize/ClassificationPreview'
import ConfidenceModeSelector from '../components/organize/ConfidenceModeSelector'

export default function Organize() {
  const [classificationResult, setClassificationResult] = useState<any>(null)

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Organize Files</h1>
        <p className="text-white/60">Upload files to automatically classify and organize them</p>
      </div>

      {/* File Upload Zone */}
      <FileUploadZone onClassificationComplete={setClassificationResult} />

      {/* Classification Preview (appears after upload) */}
      {classificationResult && (
        <ClassificationPreview
          result={classificationResult}
          onClose={() => setClassificationResult(null)}
        />
      )}

      {/* Advanced Settings (collapsible) */}
      <details className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl shadow-glass">
        <summary className="px-6 py-4 cursor-pointer text-white font-medium">
          Advanced Settings ▼
        </summary>
        <div className="px-6 pb-6">
          <ConfidenceModeSelector />
        </div>
      </details>
    </div>
  )
}
