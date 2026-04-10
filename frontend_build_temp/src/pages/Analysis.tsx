import FileAnalysisPanel from '../components/analysis/FileAnalysisPanel'

export default function Analysis() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="space-y-1">
        <h1 className="text-3xl font-bold text-white">Analysis Center</h1>
        <p className="text-white/60">Deep dive into how the AI understands your files</p>
      </div>

      <FileAnalysisPanel />
    </div>
  )
}
