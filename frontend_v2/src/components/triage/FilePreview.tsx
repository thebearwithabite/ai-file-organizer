import { useMemo } from 'react'
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
        if (['pdf'].includes(ext || '')) return 'pdf'
        if (['txt', 'md', 'json', 'xml', 'csv', 'log'].includes(ext || '')) return 'text'
        if (['py', 'js', 'ts', 'tsx', 'jsx', 'html', 'css', 'java', 'c', 'cpp'].includes(ext || '')) return 'code'
        if (['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'].includes(ext || '')) return 'office'

        return 'unknown'
    }, [fileName])

    if (fileType === 'unknown') return null

    return (
        <div className="mb-6">
            <div className="mb-4">
                {fileType === 'video' || fileType === 'audio' ? (
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
    )
}
