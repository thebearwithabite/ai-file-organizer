import { useState } from 'react'
import { motion } from 'framer-motion'
import { Check, X, RefreshCw, FileText, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '../../services/api'

interface ClassificationPreviewProps {
  result: any
  onClose: () => void
}

export default function ClassificationPreview({ result, onClose }: ClassificationPreviewProps) {
  const { classification, file_name, status, destination_path, file_path } = result
  const [isConfirming, setIsConfirming] = useState(false)
  const [project, setProject] = useState('')
  const [episode, setEpisode] = useState('')

  const handleConfirm = async () => {
    if (!file_path) {
      toast.error('File path missing - cannot classify')
      return
    }

    setIsConfirming(true)
    try {
      await api.classifyFile(
        file_path,
        classification.category,
        project || undefined,
        episode || undefined
      )

      toast.success('File organized successfully!', {
        description: `Moved to ${classification.category}`,
      })
      onClose()
    } catch (error: any) {
      toast.error('Failed to organize file', {
        description: error.message || 'Please try again',
      })
    } finally {
      setIsConfirming(false)
    }
  }

  const handleReclassify = () => {
    toast.info('Reclassification not yet implemented')
  }

  const handleSkip = () => {
    toast.info('File skipped')
    onClose()
  }

  const confidence = Math.round(classification.confidence * 100)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass"
    >
      <h3 className="text-lg font-semibold text-white mb-4">Classification Result</h3>

      {/* File Info */}
      <div className="flex items-center gap-3 mb-4 p-4 bg-white/[0.05] rounded-xl">
        <FileText size={32} className="text-blue-400" />
        <div className="flex-1">
          <div className="font-medium text-white">{file_name}</div>
          <div className="text-sm text-white/60">{status}</div>
        </div>
      </div>

      {/* AI Analysis */}
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4 mb-4">
        <div className="flex items-center gap-2 mb-2">
          <div className="text-sm font-medium text-blue-400">💡 AI Analysis</div>
          <div className={`text-xs px-2 py-1 rounded ${
            confidence >= 85 ? 'bg-success/20 text-success' :
            confidence >= 70 ? 'bg-warning/20 text-warning' :
            'bg-destructive/20 text-destructive'
          }`}>
            {confidence}% confident
          </div>
        </div>
        <p className="text-sm text-white/80 mb-3">{classification.reasoning}</p>

        {/* Confidence Bar */}
        <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${
              confidence >= 85 ? 'bg-success' :
              confidence >= 70 ? 'bg-warning' :
              'bg-destructive'
            }`}
            style={{ width: `${confidence}%` }}
          />
        </div>
      </div>

      {/* Suggested Category */}
      <div className="mb-4">
        <div className="text-xs text-white/40 mb-1">Suggested Category</div>
        <div className="text-lg font-semibold text-white">{classification.category}</div>
        {destination_path && (
          <div className="text-xs text-white/60 mt-1 truncate">→ {destination_path}</div>
        )}
      </div>

      {/* Hierarchical Organization (Optional) */}
      <div className="mb-6 space-y-3 p-3 bg-white/5 border border-white/10 rounded-xl">
        <div className="text-xs text-white/60 font-medium mb-2">
          📁 Hierarchical Organization (Optional)
        </div>

        <div>
          <label className="text-xs text-white/50 mb-1 block">Project Name</label>
          <input
            type="text"
            value={project}
            onChange={(e) => setProject(e.target.value)}
            placeholder="e.g., The_Papers_That_Dream, VEO_Prompt_Machine"
            className="w-full px-3 py-2 bg-white/5 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 placeholder:text-white/30"
          />
        </div>

        <div>
          <label className="text-xs text-white/50 mb-1 block">Episode/Version</label>
          <input
            type="text"
            value={episode}
            onChange={(e) => setEpisode(e.target.value)}
            placeholder="e.g., Episode_02_AttentionIsland"
            className="w-full px-3 py-2 bg-white/5 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 placeholder:text-white/30"
          />
        </div>

        <div className="text-xs text-white/40 italic">
          Files will be organized into: Project → Episode → Media Type
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={handleConfirm}
          disabled={isConfirming}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-success hover:bg-success/90 rounded-xl font-medium transition-colors text-white disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isConfirming ? (
            <>
              <Loader2 size={20} className="animate-spin" />
              Organizing...
            </>
          ) : (
            <>
              <Check size={20} />
              Confirm & Organize
            </>
          )}
        </button>
        <button
          onClick={handleReclassify}
          className="flex items-center justify-center gap-2 px-4 py-3 bg-white/10 hover:bg-white/20 rounded-xl font-medium transition-colors text-white"
        >
          <RefreshCw size={20} />
          Reclassify
        </button>
        <button
          onClick={handleSkip}
          className="p-3 bg-white/10 hover:bg-white/20 rounded-xl transition-colors text-white"
        >
          <X size={20} />
        </button>
      </div>

      <button
        onClick={handleSkip}
        className="w-full mt-3 text-sm text-white/60 hover:text-white transition-colors"
      >
        Skip (organize later)
      </button>
    </motion.div>
  )
}
