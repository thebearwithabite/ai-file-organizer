import { useState, useEffect } from 'react'
import { Activity, FolderOpen, Clock, Radio, Info } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '../../services/api'
import type { MonitorStatus } from '../../types/api'

export default function MonitorStatusWidget() {
  const [status, setStatus] = useState<MonitorStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Fetch monitor status
  const fetchStatus = async () => {
    try {
      const response = await api.getMonitorStatus()
      setStatus(response)
    } catch (error) {
      console.error('Error fetching monitor status:', error)
      // Don't show error toast on auto-refresh
      if (isLoading) {
        toast.error('Failed to load monitor status')
      }
    } finally {
      setIsLoading(false)
    }
  }

  // Initial fetch and auto-refresh every 30 seconds
  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  const formatUptime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)

    if (hours > 24) {
      const days = Math.floor(hours / 24)
      return `${days}d ${hours % 24}h`
    }
    if (hours > 0) {
      return `${hours}h ${minutes}m`
    }
    return `${minutes}m`
  }

  const formatLastEvent = (timestamp: string | null): string => {
    if (!timestamp) return 'No events yet'

    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins} min ago`
    if (diffHours < 24) return `${diffHours} hr ago`
    return `${diffDays} days ago`
  }

  if (isLoading || !status) {
    return (
      <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass">
        <div className="animate-pulse space-y-3">
          <div className="h-5 bg-white/10 rounded w-1/2"></div>
          <div className="h-4 bg-white/10 rounded w-3/4"></div>
          <div className="h-4 bg-white/10 rounded w-2/3"></div>
        </div>
      </div>
    )
  }

  const isActive = status.status === 'active'

  return (
    <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass animate-fade-in">
      <div className="flex items-center gap-2 mb-4">
        <Activity size={20} className={isActive ? 'text-success' : 'text-white/40'} />
        <h2 className="text-xl font-semibold text-white">Background Monitor</h2>
        <div className="group relative ml-auto">
          <Info size={16} className="text-white/40 hover:text-white/60 cursor-help transition-colors" />
          <div className="invisible group-hover:visible absolute right-0 top-6 w-72 p-3 bg-black/90 backdrop-blur-xl border border-white/20 rounded-lg text-xs text-white/80 z-10 shadow-xl">
            Watches your Downloads and Desktop folders for new files. Learns from your manual file movements (7-day cooldown rule applies). ADHD-friendly: works silently in the background without interruptions.
          </div>
        </div>
      </div>

      {/* Status Indicator */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${isActive ? 'bg-success/20' : 'bg-white/10'
              }`}>
              <Radio size={20} className={isActive ? 'text-success' : 'text-white/40'} />
            </div>
            <div>
              <div className="text-sm font-semibold text-white">
                {isActive ? 'Active' : 'Paused'}
              </div>
              <div className="text-xs text-white/60">
                {isActive ? 'Monitoring file system' : 'Not currently monitoring'}
              </div>
            </div>
          </div>
          {isActive && (
            <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
          )}
        </div>

        {/* Monitored Paths */}
        <div className="space-y-2">
          <div className="text-xs text-white/60 font-medium">Monitored Locations:</div>
          <div className="space-y-1">
            {status.paths.map((path, index) => (
              <div
                key={index}
                className="flex items-center gap-2 p-2 bg-white/5 rounded-lg"
              >
                <FolderOpen size={14} className="text-white/60 flex-shrink-0" />
                <span className="text-xs text-white/80 font-mono truncate" title={path}>
                  {path}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Statistics */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-white/5 rounded-lg">
            <div className="flex items-center gap-2 mb-1">
              <Clock size={14} className="text-white/60" />
              <div className="text-xs text-white/60">Last Event</div>
            </div>
            <div className="text-sm font-semibold text-white">
              {formatLastEvent(status.last_event)}
            </div>
          </div>

          <div className="p-3 bg-white/5 rounded-lg">
            <div className="flex items-center gap-2 mb-1">
              <Activity size={14} className="text-white/60" />
              <div className="text-xs text-white/60">Events Processed</div>
            </div>
            <div className="text-sm font-semibold text-white">
              {status.events_processed.toLocaleString()}
            </div>
          </div>
        </div>

        {/* Uptime */}
        {isActive && status.uptime_seconds > 0 && (
          <div className="p-3 bg-primary/10 border border-primary/20 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="text-xs text-primary">Monitor Uptime:</div>
              <div className="text-sm font-semibold text-primary">
                {formatUptime(status.uptime_seconds)}
              </div>
            </div>
          </div>
        )}

        {/* 7-Day Cooldown Rule Info */}
        <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
          <div className="text-xs text-white/70">
            <strong className="text-white">7-Day Learning Rule:</strong> The monitor observes your manual file movements and learns your organizational patterns. Each location has a 7-day cooldown before the AI applies learned patterns automatically.
          </div>
        </div>

        {/* Status Details */}
        {!isActive && (
          <div className="p-3 bg-warning/10 border border-warning/20 rounded-lg">
            <div className="text-xs text-warning">
              <strong>Monitor Paused:</strong> Background monitoring is currently inactive. File organization will require manual trigger or triage.
            </div>
          </div>
        )}

        {isActive && status.events_processed === 0 && (
          <div className="p-3 bg-success/10 border border-success/20 rounded-lg">
            <div className="text-xs text-success">
              <strong>Monitor Ready:</strong> Waiting for file system events. Drop files in monitored folders to see the system in action.
            </div>
          </div>
        )}

        {/* Future: Pause/Resume Controls (Placeholder) */}
        {/*
        <div className="pt-3 border-t border-white/10">
          <button
            className="w-full px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm font-medium text-white transition-colors"
          >
            {isActive ? 'Pause Monitor' : 'Resume Monitor'}
          </button>
        </div>
        */}
      </div>
    </div>
  )
}
