import { useState, useEffect } from 'react'
import { ClipboardList, ShieldAlert, CheckCircle2, XCircle, Clock, Info } from 'lucide-react'
import { api } from '../../services/api'
import type { MaintenanceLog, EmergencyLog } from '../../types/api'

type LogEntry = {
    id: string
    timestamp: string
    title: string
    details: string
    status: 'success' | 'error' | 'warning' | 'info'
    type: 'maintenance' | 'emergency'
}

export default function LogViewer() {
    const [logs, setLogs] = useState<LogEntry[]>([])
    const [activeTab, setActiveTab] = useState<'all' | 'maintenance' | 'emergency'>('all')
    const [isLoading, setIsLoading] = useState(true)

    const fetchLogs = async () => {
        try {
            const maintLogs: MaintenanceLog[] = await api.getMaintenanceLogs(20)
            const emergencyLogs: EmergencyLog[] = await api.getEmergencyLogs(20)

            const combinedLogs: LogEntry[] = [
                ...maintLogs.map((log, idx) => ({
                    id: `maint-${idx}-${log.last_run}`,
                    timestamp: log.last_run,
                    title: log.task_name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
                    details: log.details,
                    status: (log.success ? 'success' : 'error') as 'success' | 'error',
                    type: 'maintenance' as const
                })),
                ...emergencyLogs.map((log, idx) => ({
                    id: `emerg-${idx}-${log.timestamp}`,
                    timestamp: log.timestamp,
                    title: log.emergency_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
                    details: log.details,
                    status: (log.severity_level === 'emergency' ? 'error' : 'warning') as 'error' | 'warning',
                    type: 'emergency' as const
                }))
            ]

            // Sort by timestamp descending
            combinedLogs.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
            setLogs(combinedLogs)
        } catch (error) {
            console.error('Error fetching logs:', error)
        } finally {
            setIsLoading(false)
        }
    }

    useEffect(() => {
        fetchLogs()
        const interval = setInterval(fetchLogs, 60000) // Refresh every minute
        return () => clearInterval(interval)
    }, [])

    const filteredLogs = logs.filter(log =>
        activeTab === 'all' || log.type === activeTab
    )

    const formatTime = (ts: string) => {
        const date = new Date(ts)
        return date.toLocaleString([], {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    if (isLoading && logs.length === 0) {
        return (
            <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass h-[400px] flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white/30"></div>
            </div>
        )
    }

    return (
        <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass flex flex-col h-[400px]">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                    <ClipboardList size={20} className="text-primary" />
                    <h2 className="text-xl font-semibold text-white">System Logs</h2>
                </div>

                <div className="flex bg-white/5 p-1 rounded-lg">
                    {(['all', 'maintenance', 'emergency'] as const).map(tab => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${activeTab === tab
                                ? 'bg-white/10 text-white shadow-sm'
                                : 'text-white/40 hover:text-white/70'
                                }`}
                        >
                            {tab.charAt(0).toUpperCase() + tab.slice(1)}
                        </button>
                    ))}
                </div>
            </div>

            <div className="flex-1 overflow-y-auto pr-2 space-y-3 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
                {filteredLogs.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-white/40 space-y-2">
                        <Info size={32} />
                        <p className="text-sm">No {activeTab !== 'all' ? activeTab : ''} logs found</p>
                    </div>
                ) : (
                    filteredLogs.map(log => (
                        <div
                            key={log.id}
                            className="group p-3 bg-white/5 border border-white/5 rounded-xl hover:bg-white/[0.08] hover:border-white/10 transition-all duration-200"
                        >
                            <div className="flex items-start gap-3">
                                <div className="mt-0.5">
                                    {log.status === 'success' && <CheckCircle2 size={16} className="text-success" />}
                                    {log.status === 'error' && <XCircle size={16} className="text-error" />}
                                    {log.status === 'warning' && <ShieldAlert size={16} className="text-warning" />}
                                    {log.status === 'info' && <Info size={16} className="text-primary" />}
                                </div>

                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center justify-between mb-1">
                                        <h3 className="text-sm font-semibold text-white truncate group-hover:text-primary transition-colors">
                                            {log.title}
                                        </h3>
                                        <div className="flex items-center gap-1.5 text-[10px] text-white/40 font-mono">
                                            <Clock size={10} />
                                            {formatTime(log.timestamp)}
                                        </div>
                                    </div>
                                    <p className="text-xs text-white/60 line-clamp-2 leading-relaxed">
                                        {log.details}
                                    </p>
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>

            <div className="mt-4 pt-4 border-t border-white/5 flex justify-between items-center text-[10px] text-white/30">
                <p>Auto-refreshing every 60s</p>
                <div className="flex gap-3">
                    <div className="flex items-center gap-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-maintenance" />
                        Maintenance
                    </div>
                    <div className="flex items-center gap-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-error" />
                        Emergency
                    </div>
                </div>
            </div>
        </div>
    )
}
