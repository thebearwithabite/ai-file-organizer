import { useQuery } from '@tanstack/react-query'
import { formatDistanceToNow } from 'date-fns'
import { RotateCcw } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '../../services/api'
import type { FileOperation } from '../../types/api'

export default function RecentActivityFeed() {
  const { data: operations, refetch } = useQuery<FileOperation[]>({
    queryKey: ['recent-operations'],
    queryFn: api.getRecentOperations,
    refetchInterval: 5000, // Refresh every 5s for near real-time updates
  })

  const handleUndo = async (operationId: number) => {
    try {
      await api.undoOperation(operationId)
      toast.success('Operation undone', {
        description: 'Files have been restored to original locations',
      })
      refetch()
    } catch (error) {
      toast.error('Failed to undo operation', {
        description: error instanceof Error ? error.message : 'Unknown error',
      })
    }
  }

  if (!operations || operations.length === 0) {
    return (
      <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass">
        <h2 className="text-xl font-semibold text-white mb-4">Recent Activity</h2>
        <div className="text-white/40 text-center py-8">No recent activity</div>
      </div>
    )
  }

  return (
    <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass">
      <h2 className="text-xl font-semibold text-white mb-4">Recent Activity</h2>

      <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
        {operations.map((op) => (
          <div
            key={op.operation_id}
            className="flex items-start gap-4 p-4 bg-white/[0.05] rounded-xl hover:bg-white/[0.08] transition-colors group"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${op.operation_type === 'move' ? 'bg-blue-500/20 text-blue-300' :
                    op.operation_type === 'delete' ? 'bg-red-500/20 text-red-300' :
                      'bg-green-500/20 text-green-300'
                  }`}>
                  {op.operation_type.toUpperCase()}
                </span>
                <span className="text-xs text-white/40">
                  {formatDistanceToNow(new Date(op.timestamp), { addSuffix: true })}
                </span>
              </div>

              <div className="text-sm text-white/90 font-medium truncate" title={op.original_filename}>
                {op.original_filename}
              </div>

              {op.new_location && op.new_location !== op.original_path && (
                <div className="flex items-center gap-1 text-xs text-white/50 mt-1">
                  <span className="truncate max-w-[150px]">{op.original_path}</span>
                  <span>→</span>
                  <span className="text-white/70 truncate">{op.new_location}</span>
                </div>
              )}

              {op.notes && (
                <div className="text-xs text-white/30 mt-1 italic truncate">
                  {op.notes}
                </div>
              )}
            </div>

            <button
              onClick={() => handleUndo(op.operation_id)}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors opacity-0 group-hover:opacity-100"
              title="Undo this operation"
            >
              <RotateCcw size={16} className="text-warning hover:text-warning/80" />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
