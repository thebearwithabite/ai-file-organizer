import { useState, useEffect } from 'react'
import { HardDrive, AlertTriangle, Trash2, Info } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '../../services/api'
import type { SpaceProtectionStatus } from '../../types/api'

export default function DiskSpaceWidget() {
  const [status, setStatus] = useState<SpaceProtectionStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isCleaning, setIsCleaning] = useState(false)

  // Fetch space protection status
  const fetchStatus = async () => {
    try {
      const response = await api.getSpaceProtection()
      setStatus(response)
    } catch (error) {
      console.error('Error fetching space protection status:', error)
      // Don't show error toast on auto-refresh
      if (isLoading) {
        toast.error('Failed to load disk space status. Check backend connection.')
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

  const handleFreeUpSpace = async () => {
    if (!status || isCleaning) return

    try {
      setIsCleaning(true)
      await api.triggerSpaceProtection()

      toast.success('Space protection activated', {
        description: `Freed up space by moving files to safe storage`,
        duration: 4000,
      })

      // Refresh status after cleanup
      await fetchStatus()
    } catch (error) {
      console.error('Error triggering space protection:', error)
      toast.error('Failed to free up space')
    } finally {
      setIsCleaning(false)
    }
  }

  // Determine color based on usage percentage
  const getGaugeColor = (percent: number) => {
    if (percent < 80) return 'bg-success'
    if (percent < 95) return 'bg-warning'
    return 'bg-destructive'
  }

  const getStatusColor = (statusType: string) => {
    if (statusType === 'healthy') return 'text-success'
    if (statusType === 'warning') return 'text-warning'
    return 'text-destructive'
  }

  const getStatusBgColor = (statusType: string) => {
    if (statusType === 'healthy') return 'bg-success/20'
    if (statusType === 'warning') return 'bg-warning/20'
    return 'bg-destructive/20'
  }

  const getStatusBorderColor = (statusType: string) => {
    if (statusType === 'healthy') return 'border-success/30'
    if (statusType === 'warning') return 'border-warning/30'
    return 'border-destructive/30'
  }

  if (isLoading || !status) {
    return (
      <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-white/10 rounded w-1/2"></div>
          <div className="h-2 bg-white/10 rounded"></div>
          <div className="h-8 bg-white/10 rounded w-1/3"></div>
        </div>
      </div>
    )
  }

  // Null-safe extraction of values with defaults
  const usedPercent = status?.used_percent ?? 0
  const freeGb = status?.free_gb ?? 0
  const totalGb = status?.total_gb ?? 0
  const statusType = status?.status ?? 'unknown'

  return (
    <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass animate-fade-in">
      <div className="flex items-center gap-2 mb-4">
        <HardDrive size={20} className="text-purple-400" />
        <h2 className="text-xl font-semibold text-white">Disk Space Protection</h2>
        <div className="group relative ml-auto">
          <Info size={16} className="text-white/40 hover:text-white/60 cursor-help transition-colors" />
          <div className="invisible group-hover:visible absolute right-0 top-6 w-72 p-3 bg-black/90 backdrop-blur-xl border border-white/20 rounded-lg text-xs text-white/80 z-10 shadow-xl">
            Monitors disk space and prevents "disk full" crises. Automatically protects against space issues before they happen. ADHD-friendly: eliminates panic moments from sudden space issues.
          </div>
        </div>
      </div>

      {/* Disk Usage Stats */}
      <div className="space-y-4">
        {/* Usage Percentage */}
        <div className="flex items-baseline justify-between">
          <div>
            <div className="text-3xl font-bold text-white">{usedPercent.toFixed(1)}%</div>
            <div className="text-xs text-white/60">Local Disk Usage</div>
          </div>
          <div className={`px-3 py-1 rounded-lg text-xs font-semibold ${getStatusBgColor(statusType)
            } ${getStatusColor(statusType)
            } border ${getStatusBorderColor(statusType)
            }`}>
            {statusType.toUpperCase()}
          </div>
        </div>

        {/* Horizontal Gauge Bar */}
        <div className="space-y-2">
          <div className="w-full h-3 bg-white/10 rounded-full overflow-hidden relative">
            <div
              className={`h-full rounded-full transition-all duration-1000 ease-out ${getGaugeColor(usedPercent)
                }`}
              style={{ width: `${usedPercent}%` }}
            />

            {/* Threshold markers */}
            <div className="absolute top-0 left-[80%] w-0.5 h-full bg-white/30" title="80% threshold" />
            <div className="absolute top-0 left-[95%] w-0.5 h-full bg-white/50" title="95% threshold" />
          </div>

          {/* Storage Info */}
          <div className="flex items-center justify-between text-xs text-white/60">
            <div>
              <span className="font-mono">{freeGb.toFixed(1)} GB</span> free
            </div>
            <div>
              <span className="font-mono">{totalGb.toFixed(1)} GB</span> total
            </div>
          </div>
        </div>

        {/* Warning Indicators */}
        {(status?.threshold_85 || status?.threshold_95) && (
          <div className={`p-3 rounded-lg border flex items-start gap-3 ${status?.threshold_95
            ? 'bg-destructive/20 border-destructive/30'
            : 'bg-warning/20 border-warning/30'
            }`}>
            <AlertTriangle size={16} className={status?.threshold_95 ? 'text-destructive' : 'text-warning'} />
            <div className="flex-1">
              <div className={`text-sm font-semibold mb-1 ${status?.threshold_95 ? 'text-destructive' : 'text-warning'
                }`}>
                {status?.threshold_95 ? 'Critical: Low Disk Space!' : 'Warning: Disk Space Running Low'}
              </div>
              <div className="text-xs text-white/70">
                {status?.threshold_95
                  ? 'Your disk is nearly full. Free up space now to prevent issues.'
                  : 'Consider freeing up space soon to maintain optimal performance.'}
              </div>
            </div>
          </div>
        )}

        {/* Free Up Space Button */}
        {(status?.threshold_85 || status?.threshold_95) && (
          <button
            onClick={handleFreeUpSpace}
            disabled={isCleaning}
            className={`w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-all duration-200 ${status?.threshold_95
              ? 'bg-destructive hover:bg-destructive/80 text-white shadow-lg'
              : 'bg-warning hover:bg-warning/80 text-black shadow-lg'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <Trash2 size={16} />
            {isCleaning ? 'Freeing Space...' : 'Free Up Space Now'}
          </button>
        )}

        {/* Healthy Status */}
        {statusType === 'healthy' && (
          <div className="p-3 bg-success/10 border border-success/20 rounded-lg">
            <div className="text-xs text-success">
              <strong>Status: Healthy</strong> - Disk space is in good condition. No action needed.
            </div>
          </div>
        )}

        {/* Threshold Legend */}
        <div className="pt-3 border-t border-white/10">
          <div className="text-xs text-white/40 space-y-1">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-success"></div>
              <span>&lt; 80%: Healthy</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-warning"></div>
              <span>80-95%: Warning</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-destructive"></div>
              <span>&gt; 95%: Critical</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
