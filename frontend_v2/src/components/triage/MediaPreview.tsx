import { useState, useRef, useEffect } from 'react'
import { Play, Pause, Volume2, VolumeX } from 'lucide-react'

interface MediaPreviewProps {
    filePath: string
    fileType: 'video' | 'audio'
}

export default function MediaPreview({ filePath, fileType }: MediaPreviewProps) {
    const [isPlaying, setIsPlaying] = useState(false)
    const [isMuted, setIsMuted] = useState(false)
    const [progress, setProgress] = useState(0)
    const [error, setError] = useState<string | null>(null)

    const mediaRef = useRef<HTMLVideoElement | HTMLAudioElement>(null)
    const MAX_AUDIO_DURATION = 15 // seconds

    // Construct the streaming URL
    // Use encodeURIComponent to handle spaces and special characters in paths
    const mediaUrl = `/api/files/content?path=${encodeURIComponent(filePath)}`

    useEffect(() => {
        const media = mediaRef.current
        if (!media) return

        const handleTimeUpdate = () => {
            if (media.duration) {
                setProgress((media.currentTime / media.duration) * 100)
            }

            // Auto-stop audio after 15 seconds
            if (fileType === 'audio' && media.currentTime >= MAX_AUDIO_DURATION) {
                media.pause()
                media.currentTime = 0
                setIsPlaying(false)
            }
        }

        const handleEnded = () => {
            setIsPlaying(false)
            setProgress(0)
        }

        const handleError = () => {
            setError('Failed to load media. Format may not be supported.')
            setIsPlaying(false)
        }

        media.addEventListener('timeupdate', handleTimeUpdate)
        media.addEventListener('ended', handleEnded)
        media.addEventListener('error', handleError)

        return () => {
            media.removeEventListener('timeupdate', handleTimeUpdate)
            media.removeEventListener('ended', handleEnded)
            media.removeEventListener('error', handleError)
        }
    }, [fileType])

    const togglePlay = () => {
        if (mediaRef.current) {
            if (isPlaying) {
                mediaRef.current.pause()
            } else {
                mediaRef.current.play()
            }
            setIsPlaying(!isPlaying)
        }
    }

    const toggleMute = () => {
        if (mediaRef.current) {
            mediaRef.current.muted = !isMuted
            setIsMuted(!isMuted)
        }
    }

    if (error) {
        return (
            <div className="w-full h-48 bg-black/20 rounded-lg flex items-center justify-center text-white/50 text-sm">
                {error}
            </div>
        )
    }

    return (
        <div className="w-full bg-black/40 rounded-xl overflow-hidden border border-white/10">
            {fileType === 'video' ? (
                <video
                    ref={mediaRef as React.RefObject<HTMLVideoElement>}
                    src={mediaUrl}
                    className="w-full aspect-video object-contain bg-black"
                    onClick={togglePlay}
                />
            ) : (
                <audio
                    ref={mediaRef as React.RefObject<HTMLAudioElement>}
                    src={mediaUrl}
                />
            )}

            {/* Controls */}
            <div className="p-3 flex items-center gap-3 bg-white/5 backdrop-blur-sm">
                <button
                    onClick={togglePlay}
                    className="p-2 hover:bg-white/10 rounded-full transition-colors text-white"
                >
                    {isPlaying ? <Pause size={20} /> : <Play size={20} />}
                </button>

                <div className="flex-1 h-1 bg-white/10 rounded-full overflow-hidden">
                    <div
                        className="h-full bg-primary transition-all duration-100"
                        style={{ width: `${progress}%` }}
                    />
                </div>

                <button
                    onClick={toggleMute}
                    className="p-2 hover:bg-white/10 rounded-full transition-colors text-white/70"
                >
                    {isMuted ? <VolumeX size={18} /> : <Volume2 size={18} />}
                </button>

                {fileType === 'audio' && (
                    <span className="text-xs text-white/50 font-mono">
                        Preview (15s)
                    </span>
                )}
            </div>
        </div>
    )
}
