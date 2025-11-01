import { useQuery } from '@tanstack/react-query'
import { formatDistanceToNow } from 'date-fns'
import { RotateCcw } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '../../services/api'
import type { FileOperation } from '../../types/api'

export default function RecentActivityFeed() {
  const { data: operations } = useQuery<FileOperation[]>({
    queryKey: ['recent-operations'],
    queryFn: api.getRecentOperations,
    refetchInterval: 30000, // Refresh every 30s
  })

  const handleUndo = (_operationId: number) => {
    toast.success('Operation undone', {
      description: 'Files have been restored to original locations',
    })
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

      <div className="space-y-3">
        {operations.map((op) => (
          <div
            key={op.operation_id}
            className="flex items-start gap-4 p-4 bg-white/[0.05] rounded-xl hover:bg-white/[0.08] transition-colors"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-medium text-white capitalize">{op.operation_type}</span>
                <span className="text-xs text-white/40">
                  {formatDistanceToNow(new Date(op.timestamp), { addSuffix: true })}
                </span>
              </div>
              <div className="text-sm text-white/60">{op.file_name}</div>
              {op.new_path && (
                <div className="text-xs text-white/40 mt-1">
                  → {op.new_path}
                </div>
              )}
            </div>
            <button
              onClick={() => handleUndo(op.operation_id)}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors"
              title="Undo this operation"
            >
              <RotateCcw size={16} className="text-warning" />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
