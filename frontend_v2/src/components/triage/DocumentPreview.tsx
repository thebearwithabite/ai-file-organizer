import { useState, useEffect } from 'react'
import { FileText, Code, AlertCircle } from 'lucide-react'

interface DocumentPreviewProps {
    filePath: string
    fileType: 'pdf' | 'text' | 'office' | 'code'
}

export default function DocumentPreview({ filePath, fileType }: DocumentPreviewProps) {
    const [content, setContent] = useState<string>('')
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const fileUrl = `/api/files/content?path=${encodeURIComponent(filePath)}`
    const textPreviewUrl = `/api/files/preview-text?path=${encodeURIComponent(filePath)}`

    useEffect(() => {
        const fetchContent = async () => {
            if (fileType === 'pdf') return // PDF handled by iframe

            setIsLoading(true)
            setError(null)

            try {
                const url = fileType === 'office' ? textPreviewUrl : fileUrl
                const response = await fetch(url)

                if (!response.ok) throw new Error('Failed to load content')

                if (fileType === 'office') {
                    const data = await response.json()
                    setContent(data.text || 'No text content found.')
                } else {
                    const text = await response.text()
                    // Limit text preview size for performance
                    setContent(text.slice(0, 10000) + (text.length > 10000 ? '\n... (truncated)' : ''))
                }
            } catch (err) {
                setError('Failed to load document preview.')
                console.error(err)
            } finally {
                setIsLoading(false)
            }
        }

        fetchContent()
    }, [filePath, fileType])

    if (fileType === 'pdf') {
        return (
            <div className="w-full h-[500px] bg-white/5 rounded-xl overflow-hidden border border-white/10">
                <object
                    data={fileUrl}
                    type="application/pdf"
                    className="w-full h-full"
                >
                    <div className="flex flex-col items-center justify-center h-full text-white/60">
                        <p>PDF preview not supported in this browser.</p>
                        <a
                            href={fileUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-2 text-primary hover:underline"
                        >
                            Open PDF in new tab
                        </a>
                    </div>
                </object>
            </div>
        )
    }

    return (
        <div className="w-full bg-black/40 rounded-xl overflow-hidden border border-white/10 flex flex-col">
            {/* Header */}
            <div className="px-4 py-2 bg-white/5 border-b border-white/10 flex items-center gap-2">
                {fileType === 'code' ? <Code size={16} className="text-blue-400" /> : <FileText size={16} className="text-orange-400" />}
                <span className="text-xs font-medium text-white/70 uppercase tracking-wider">
                    {fileType === 'office' ? 'Text Extraction Preview' : 'File Content'}
                </span>
            </div>

            {/* Content */}
            <div className="p-4 max-h-[400px] overflow-y-auto font-mono text-sm text-white/80 whitespace-pre-wrap scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
                {isLoading ? (
                    <div className="flex items-center justify-center py-8 text-white/40">
                        Loading content...
                    </div>
                ) : error ? (
                    <div className="flex items-center gap-2 text-destructive py-4">
                        <AlertCircle size={16} />
                        <span>{error}</span>
                    </div>
                ) : (
                    content
                )}
            </div>
        </div>
    )
}
