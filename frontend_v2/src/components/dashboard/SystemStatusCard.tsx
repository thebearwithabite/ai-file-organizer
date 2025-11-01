import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { HardDrive, Cloud, Activity, Trash2 } from 'lucide-react'
import { api } from '../../services/api'
import { toast } from 'sonner'
import type { SystemStatus } from '../../types/api'

export default function SystemStatusCard() {
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery<SystemStatus>({
    queryKey: ['system-status'],
    queryFn: api.getSystemStatus,
    refetchInterval: 10000, // Refresh every 10s
  })

  const cleanupMutation = useMutation({
    mutationFn: api.emergencyCleanup,
    onSuccess: (result) => {
      toast.success(`Freed ${result.freed_mb}MB by moving ${result.moved_count} files to Google Drive`)
      queryClient.invalidateQueries({ queryKey: ['system-status'] })
    },
    onError: () => {
      toast.error('Emergency cleanup failed')
    }
  })

  if (isLoading || !data) {
    return (
      <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass">
        <div className="animate-pulse text-white/60">Loading system status...</div>
      </div>
    )
  }

  const status = data

  return (
    <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass">
      <h2 className="text-xl font-semibold text-white mb-4">System Status</h2>

      <div className="space-y-4">
        {/* Google Drive */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Cloud size={20} className="text-blue-400" />
            <div>
              <div className="text-sm font-medium text-white">Google Drive</div>
              <div className="text-xs text-white/60">
                {status.google_drive.connected
                  ? `Connected as ${status.google_drive.user_name}`
                  : 'Not connected'}
              </div>
            </div>
          </div>
          <div className={`w-2 h-2 rounded-full ${status.google_drive.connected ? 'bg-success' : 'bg-destructive'}`} />
        </div>

        {/* Disk Space */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <HardDrive size={20} className="text-purple-400" />
              <div>
                <div className="text-sm font-medium text-white">Disk Space</div>
                <div className="text-xs text-white/60">
                  {status.disk_space.free_gb}GB free / {status.disk_space.total_gb}GB total
                </div>
              </div>
            </div>
            <div className={`px-2 py-1 rounded text-xs font-medium ${
              status.disk_space.status === 'safe' ? 'bg-success/20 text-success' :
              status.disk_space.status === 'warning' ? 'bg-warning/20 text-warning' :
              'bg-destructive/20 text-destructive'
            }`}>
              {status.disk_space.status}
            </div>
          </div>
          {/* Visual progress bar */}
          <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                status.disk_space.percent_used < 70 ? 'bg-success' :
                status.disk_space.percent_used < 85 ? 'bg-warning' :
                'bg-destructive'
              }`}
              style={{ width: `${status.disk_space.percent_used}%` }}
            />
          </div>

          {/* Emergency Cleanup Button (only show if space is low) */}
          {status.disk_space.status !== 'safe' && (
            <button
              onClick={() => cleanupMutation.mutate()}
              disabled={cleanupMutation.isPending}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 mt-2 bg-warning/20 hover:bg-warning/30 border border-warning/30 rounded-lg text-xs font-medium text-warning transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Trash2 size={14} />
              {cleanupMutation.isPending ? 'Freeing space...' : 'Free Up Space (Move to Google Drive)'}
            </button>
          )}
        </div>

        {/* Background Services */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Activity size={20} className="text-green-400" />
            <div>
              <div className="text-sm font-medium text-white">Background Services</div>
              <div className="text-xs text-white/60">3 services running</div>
            </div>
          </div>
          <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
        </div>

        {/* Confidence Mode */}
        <div className="pt-4 border-t border-white/10">
          <div className="text-xs text-white/40 mb-1">Confidence Mode</div>
          <div className="text-sm font-medium text-white capitalize">
            {status.confidence_mode} Mode
          </div>
        </div>
      </div>
    </div>
  )
}
