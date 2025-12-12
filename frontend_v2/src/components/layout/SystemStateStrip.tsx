import { useState, useEffect } from 'react'
import { api } from '../../services/api'
import type { SystemStatus } from '../../types/api'

export default function SystemStateStrip() {
    const [status, setStatus] = useState<SystemStatus | null>(null)
    const [error, setError] = useState(false)

    const fetchStatus = async () => {
        try {
            const data = await api.getSystemStatus()
            setStatus(data)
            setError(false)
        } catch (err) {
            console.error('Failed to fetch system status:', err)
            setError(true)
        }
    }

    useEffect(() => {
        fetchStatus()
        const interval = setInterval(fetchStatus, 30000)
        return () => clearInterval(interval)
    }, [])

    // Status helpers
    const getBackendStatus = () => {
        if (error) return { label: 'Offline', color: 'bg-red-500' }
        if (!status) return { label: 'Checking...', color: 'bg-gray-500' }

        // Check backend status if available, fallback to defaults
        const s = status.backend_status || 'degraded'
        if (s === 'ok') return { label: 'OK', color: 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' }
        if (s === 'degraded') return { label: 'Degraded', color: 'bg-orange-500' }
        return { label: 'Error', color: 'bg-red-500' }
    }

    const getMonitorStatus = () => {
        if (error || !status) return { label: '-', color: 'bg-gray-500' }

        if (status.monitor) {
            return {
                label: `Watching ${status.monitor.watching_paths ?? 0} folders · ${status.monitor.rules_loaded ?? 0} rules`,
                color: 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]'
            }
        }
        return { label: 'Monitor unavailable', color: 'bg-orange-500' }
    }

    const getOrchestrationStatus = () => {
        if (error || !status) return { label: '-', color: 'bg-gray-500' }

        if (status.orchestration && status.orchestration.last_run) {
            const date = new Date(status.orchestration.last_run)
            const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            const files = status.orchestration.files_touched ?? 0
            return {
                label: `${timeStr} (${files} files)`,
                color: 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]'
            }
        }
        return { label: 'Never run', color: 'bg-gray-500' }
    }

    const backend = getBackendStatus()
    const monitor = getMonitorStatus()
    const orchestration = getOrchestrationStatus()

    return (
        <div className="w-full bg-slate-900/95 border-b border-slate-800 backdrop-blur-md px-6 py-2 flex items-center gap-8 text-sm text-slate-300 z-50 sticky top-0 h-10">
            {/* Backend */}
            <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${backend.color}`}></span>
                <span className="opacity-70">Backend:</span>
                <span className="font-medium text-white">{backend.label}</span>
            </div>

            {/* Monitor */}
            <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${monitor.color}`}></span>
                <span className="opacity-70">Monitor:</span>
                <span className="font-medium text-white">{monitor.label}</span>
            </div>

            {/* Orchestration */}
            <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${orchestration.color}`}></span>
                <span className="opacity-70">Last Orchestration:</span>
                <span className="font-medium text-white">{orchestration.label}</span>
            </div>
        </div>
    )
}
