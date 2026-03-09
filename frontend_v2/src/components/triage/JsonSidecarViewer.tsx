import { useState, useEffect, useId } from 'react'
import { FileJson, ChevronDown, ChevronRight } from 'lucide-react'

interface JsonSidecarViewerProps {
    filePath: string
}

export default function JsonSidecarViewer({ filePath }: JsonSidecarViewerProps) {
    const [data, setData] = useState<any>(null)
    const [isOpen, setIsOpen] = useState(false)
    const [isLoading, setIsLoading] = useState(false)
    const [exists, setExists] = useState(false)
    const buttonId = useId()
    const contentId = useId()

    // Sidecar path is usually original path + .json
    const sidecarPath = `${filePath}.json`
    const sidecarUrl = `/api/files/content?path=${encodeURIComponent(sidecarPath)}`

    useEffect(() => {
        const checkSidecar = async () => {
            setIsLoading(true)
            try {
                const response = await fetch(sidecarUrl)
                if (response.ok) {
                    const jsonData = await response.json()
                    setData(jsonData)
                    setExists(true)
                } else {
                    setExists(false)
                }
            } catch (err) {
                setExists(false)
            } finally {
                setIsLoading(false)
            }
        }

        checkSidecar()
    }, [filePath])

    if (!exists && !isLoading) return null

    return (
        <div className="mt-4 border border-white/10 rounded-xl overflow-hidden bg-white/5">
            <button
                id={buttonId}
                onClick={() => setIsOpen(!isOpen)}
                aria-expanded={isOpen}
                aria-controls={contentId}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-inset"
            >
                <div className="flex items-center gap-2 text-sm font-medium text-white/80">
                    <FileJson size={16} className="text-yellow-400" aria-hidden="true" />
                    <span>Sidecar Metadata</span>
                    {isLoading && <span className="text-xs text-white/40 ml-2" aria-live="polite">(Loading...)</span>}
                </div>
                {isOpen ? (
                    <ChevronDown size={16} className="text-white/40" aria-hidden="true" />
                ) : (
                    <ChevronRight size={16} className="text-white/40" aria-hidden="true" />
                )}
            </button>

            {isOpen && data && (
                <div
                    id={contentId}
                    role="region"
                    aria-labelledby={buttonId}
                    className="p-4 bg-black/20 border-t border-white/10 font-mono text-xs text-white/70 overflow-x-auto"
                >
                    <pre>{JSON.stringify(data, null, 2)}</pre>
                </div>
            )}
        </div>
    )
}
