import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, CheckCircle, AlertTriangle, Loader2, Brain, ChevronRight } from 'lucide-react'
import { api } from '../../services/api'
import { toast } from 'sonner'
import type { ClassificationResult } from '../../types/api'

export default function FileAnalysisPanel() {
    const [analyzing, setAnalyzing] = useState(false)
    const [result, setResult] = useState<ClassificationResult | null>(null)

    const onDrop = useCallback(async (acceptedFiles: File[]) => {
        const file = acceptedFiles[0]
        if (!file) return

        setAnalyzing(true)
        setResult(null)

        try {
            const data = await api.uploadFile(file)
            setResult(data)
            toast.success('Analysis complete')
        } catch (error: any) {
            console.error('Analysis failed:', error)
            toast.error('Analysis failed', { description: error.message })
        } finally {
            setAnalyzing(false)
        }
    }, [])

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        maxFiles: 1,
        multiple: false
    })

    const getScoreColor = (score: number) => {
        if (score >= 0.85) return 'text-success'
        if (score >= 0.70) return 'text-warning'
        return 'text-destructive'
    }

    const getScoreBg = (score: number) => {
        if (score >= 0.85) return 'bg-success/10 border-success/20'
        if (score >= 0.70) return 'bg-warning/10 border-warning/20'
        return 'bg-destructive/10 border-destructive/20'
    }

    return (
        <div className="space-y-6">
            <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass">
                <div className="flex items-center gap-3 mb-4">
                    <Brain size={24} className="text-primary" />
                    <div>
                        <h2 className="text-xl font-semibold text-white">AI File Analyst</h2>
                        <p className="text-sm text-white/60">Upload a file to see how the AI understands and classifies it.</p>
                    </div>
                </div>

                {/* Dropzone */}
                <div
                    {...getRootProps()}
                    className={`border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer ${isDragActive
                        ? 'border-primary bg-primary/10'
                        : 'border-white/10 hover:border-white/20 hover:bg-white/5'
                        }`}
                >
                    <input {...getInputProps()} />
                    <div className="flex flex-col items-center gap-4">
                        <div className={`p-4 rounded-full ${isDragActive ? 'bg-primary/20' : 'bg-white/5'}`}>
                            <Upload size={32} className={isDragActive ? 'text-primary' : 'text-white/40'} />
                        </div>
                        <div>
                            <p className="text-lg font-medium text-white">
                                {isDragActive ? 'Drop file to analyze' : 'Drag & drop a file here'}
                            </p>
                            <p className="text-sm text-white/40 mt-1">or click to browse</p>
                        </div>
                        <div className="text-xs text-white/30 border border-white/10 rounded-full px-3 py-1">
                            Supports documents, images, audio, and video
                        </div>
                    </div>
                </div>
            </div>

            {/* Loading State */}
            {analyzing && (
                <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-12 shadow-glass text-center animate-pulse">
                    <Loader2 size={48} className="mx-auto text-primary mb-4 animate-spin" />
                    <h3 className="text-xl font-semibold text-white mb-2">Analyzing Content...</h3>
                    <p className="text-white/60">Using vision and text logic to categorize your file</p>
                </div>
            )}

            {/* Analysis Result */}
            {result && !analyzing && (
                <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden shadow-glass animate-fade-in">
                    {/* Header */}
                    <div className="p-6 border-b border-white/10 bg-white/5">
                        <div className="flex items-start justify-between">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-white/10 rounded-xl">
                                    <FileText size={24} className="text-blue-400" />
                                </div>
                                <div>
                                    <h3 className="text-lg font-bold text-white">{result.file_name}</h3>
                                    <div className="flex items-center gap-2 text-sm text-white/60">
                                        <span>Detected as:</span>
                                        <span className="text-white font-medium px-2 py-0.5 rounded bg-white/10 uppercase text-xs">
                                            {result.classification.category}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            <div className="text-right">
                                <div className={`text-2xl font-bold ${getScoreColor(result.classification.confidence)}`}>
                                    {Math.round(result.classification.confidence * 100)}%
                                </div>
                                <div className="text-xs text-white/40">Confidence Score</div>
                            </div>
                        </div>
                    </div>

                    <div className="p-6 space-y-6">
                        {/* Reasoning Box */}
                        <div className={`p-4 rounded-xl ${getScoreBg(result.classification.confidence)}`}>
                            <div className="flex items-start gap-3">
                                <div className="mt-1">
                                    {result.classification.confidence >= 0.85 ? (
                                        <CheckCircle size={20} className="text-success" />
                                    ) : (
                                        <AlertTriangle size={20} className={getScoreColor(result.classification.confidence)} />
                                    )}
                                </div>
                                <div>
                                    <h4 className={`text-sm font-semibold mb-1 ${getScoreColor(result.classification.confidence)}`}>
                                        Why this category?
                                    </h4>
                                    <p className="text-white/80 text-sm leading-relaxed">
                                        {result.classification.reasoning}
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Path Prediction */}
                        <div className="space-y-2">
                            <h4 className="text-sm font-medium text-white/60">Predicted Destination</h4>
                            <div className="flex items-center gap-2 p-3 bg-black/20 rounded-lg font-mono text-sm text-white/80 break-all">
                                <ChevronRight size={16} className="text-white/40 flex-shrink-0" />
                                {result.destination_path}
                            </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex gap-3 pt-2">
                            <button
                                onClick={() => setResult(null)}
                                className="flex-1 py-2 px-4 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-white/80 transition-colors"
                            >
                                Analyze Another File
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
