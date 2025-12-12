import { useState, useEffect } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'
import { api } from '../../services/api'

export default function ConnectionStatus() {
    const [isOnline, setIsOnline] = useState(true)
    const [isChecking, setIsChecking] = useState(false)

    const checkConnection = async () => {
        setIsChecking(true)
        try {
            await api.getSystemStatus()
            setIsOnline(true)
        } catch (error) {
            setIsOnline(false)
        } finally {
            setIsChecking(false)
        }
    }

    useEffect(() => {
        // Initial check
        checkConnection()

        // Poll every 5 seconds
        const interval = setInterval(checkConnection, 5000)
        return () => clearInterval(interval)
    }, [])

    if (isOnline) return null

    return (
        <div className="bg-destructive text-destructive-foreground px-4 py-2 flex items-center justify-between shadow-md animate-in slide-in-from-top duration-300">
            <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4" />
                <span className="text-sm font-medium">
                    Backend Disconnected. Trying to reconnect...
                </span>
            </div>
            <button
                onClick={checkConnection}
                disabled={isChecking}
                className="text-xs bg-background/20 hover:bg-background/30 px-2 py-1 rounded flex items-center gap-1 transition-colors"
            >
                <RefreshCw className={`h-3 w-3 ${isChecking ? 'animate-spin' : ''}`} />
                Retry Now
            </button>
        </div>
    )
}
