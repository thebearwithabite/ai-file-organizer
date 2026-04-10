import { useState, useEffect } from 'react'
import { FileJson, ChevronDown, ChevronRight } from 'lucide-react'

interface JsonSidecarViewerProps {
    filePath: string
}

export default function JsonSidecarViewer({ filePath }: JsonSidecarViewerProps) {
    const [data, setData] = useState<any>(null)
    const [isOpen, setIsOpen] = useState(false)
    const [isLoading, setIsLoading] = useState(false)
    const [exists, setExists] = useState(false)

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
                onClick={() => setIsOpen(!isOpen)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/5 transition-colors"
            >
                <div className="flex items-center gap-2 text-sm font-medium text-white/80">
                    <FileJson size={16} className="text-yellow-400" />
                    <span>Sidecar Metadata</span>
                    {isLoading && <span className="text-xs text-white/40 ml-2">(Loading...)</span>}
                </div>
                {isOpen ? <ChevronDown size={16} className="text-white/40" /> : <ChevronRight size={16} className="text-white/40" />}
            </button>

            {isOpen && data && (
                <div className="p-4 bg-black/20 border-t border-white/10 font-mono text-xs text-white/70 overflow-x-auto">
                    <pre>{JSON.stringify(data, null, 2)}</pre>
                </div>
            )}
        </div>
    )
}
