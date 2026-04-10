import { useState, useMemo } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import MediaPreview from './MediaPreview'
import DocumentPreview from './DocumentPreview'
import JsonSidecarViewer from './JsonSidecarViewer'

interface FilePreviewProps {
    filePath: string
    fileName: string
}

export default function FilePreview({ filePath, fileName }: FilePreviewProps) {
    const fileType = useMemo(() => {
        const ext = fileName.split('.').pop()?.toLowerCase()

        if (['mp4', 'mov', 'avi', 'mkv', 'webm'].includes(ext || '')) return 'video'
        if (['mp3', 'wav', 'm4a', 'flac', 'ogg'].includes(ext || '')) return 'audio'
        if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'heic'].includes(ext || '')) return 'image'
        if (['pdf'].includes(ext || '')) return 'pdf'
        if (['txt', 'md', 'json', 'xml', 'csv', 'log'].includes(ext || '')) return 'text'
        if (['py', 'js', 'ts', 'tsx', 'jsx', 'html', 'css', 'java', 'c', 'cpp'].includes(ext || '')) return 'code'
        if (['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'].includes(ext || '')) return 'office'

        return 'unknown'
    }, [fileName])

    const [isOpen, setIsOpen] = useState(fileType === 'image')

    // Basic fallback for opening files we don't preview natively
    const handleOpenFile = async () => {
        try {
            await fetch('/api/open-file', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: filePath })
            })
        } catch (e) {
            console.error("Failed to open file", e)
        }
    }

    if (fileType === 'unknown') {
        return (
            <div className="mb-6 mt-2">
                <button
                    onClick={handleOpenFile}
                    className="text-sm font-medium text-primary hover:underline flex items-center gap-2"
                >
                    🔗 Open "{fileName}" externally
                </button>
                <JsonSidecarViewer filePath={filePath} />
            </div>
        )
    }

    return (
        <div className="mb-6 mt-2 border border-white/10 bg-black/20 rounded-xl overflow-hidden">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between p-3 bg-white/5 hover:bg-white/10 transition-colors text-sm font-medium text-white/80"
            >
                <div className="flex items-center gap-2">
                    {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    {fileType === 'image' ? '🖼️ Image Preview' : fileType === 'pdf' ? '📄 PDF Preview' : 'Preview Document'}
                </div>
            </button>

            {isOpen && (
                <div className="p-4 border-t border-white/10">
                    <div className="mb-4">
                        {fileType === 'image' ? (
                            <div className="bg-black/20 rounded-xl overflow-hidden border border-white/10 max-w-sm">
                                <img
                                    src={`/api/files/content?path=${encodeURIComponent(filePath)}`}
                                    alt={fileName}
                                    className="w-full h-auto max-h-64 object-contain"
                                    loading="lazy"
                                />
                            </div>
                        ) : fileType === 'video' || fileType === 'audio' ? (
                            <MediaPreview filePath={filePath} fileType={fileType} />
                        ) : (
                            <DocumentPreview
                                filePath={filePath}
                                fileType={fileType as 'pdf' | 'text' | 'office' | 'code'}
                            />
                        )}
                    </div>

                    <JsonSidecarViewer filePath={filePath} />
                </div>
            )}
        </div>
    )
}
