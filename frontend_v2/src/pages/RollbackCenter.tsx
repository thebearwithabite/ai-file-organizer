import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Undo2, AlertTriangle, Search, Clock, FileText, FolderOpen } from 'lucide-react'
import { api } from '../services/api'
import { toast } from 'sonner'
import type { RollbackOperation } from '../types/api'

export default function RollbackCenter() {
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState('')
  const [timeFilter, setTimeFilter] = useState<'today' | '7days' | '30days'>('30days')

  const { data, isLoading } = useQuery({
    queryKey: ['rollback-operations', timeFilter, searchTerm],
    queryFn: () => api.getRollbackOperations({
      days: timeFilter === 'today' ? 1 : timeFilter === '7days' ? 7 : 30,
      todayOnly: timeFilter === 'today',
      search: searchTerm || undefined,
    }),
    refetchInterval: 5000, // Refresh every 5s
  })

  const undoMutation = useMutation({
    mutationFn: api.undoOperation,
    onSuccess: (result) => {
      toast.success(result.message || 'Operation undone successfully')
      queryClient.invalidateQueries({ queryKey: ['rollback-operations'] })
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to undo operation')
    },
  })

  const undoTodayMutation = useMutation({
    mutationFn: api.undoToday,
    onSuccess: (result) => {
      toast.success(`${result.count} operations undone successfully`)
      queryClient.invalidateQueries({ queryKey: ['rollback-operations'] })
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to undo today's operations")
    },
  })

  const operations: RollbackOperation[] = data?.operations || []

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Rollback Center</h1>
          <p className="text-white/60 mt-1">Safely undo file operations and restore files</p>
        </div>

        {/* Emergency Undo Today Button */}
        {operations.some(op => {
          const opDate = new Date(op.timestamp)
          const today = new Date()
          return opDate.toDateString() === today.toDateString()
        }) && (
            <button
              onClick={() => {
                if (window.confirm('⚠️ This will undo ALL file operations from today. Are you sure?')) {
                  undoTodayMutation.mutate()
                }
              }}
              disabled={undoTodayMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-destructive/20 hover:bg-destructive/30 border border-destructive/30 rounded-lg text-sm font-medium text-destructive transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <AlertTriangle size={16} />
              {undoTodayMutation.isPending ? 'Undoing...' : 'Emergency Undo Today'}
            </button>
          )}
      </div>

      {/* Controls */}
      <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-4 shadow-glass">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" size={18} />
              <input
                type="text"
                placeholder="Search by filename or path..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>
          </div>

          {/* Time Filter */}
          <div className="flex gap-2">
            <button
              onClick={() => setTimeFilter('today')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${timeFilter === 'today'
                  ? 'bg-primary text-white'
                  : 'bg-white/5 text-white/60 hover:bg-white/10'
                }`}
            >
              Today
            </button>
            <button
              onClick={() => setTimeFilter('7days')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${timeFilter === '7days'
                  ? 'bg-primary text-white'
                  : 'bg-white/5 text-white/60 hover:bg-white/10'
                }`}
            >
              7 Days
            </button>
            <button
              onClick={() => setTimeFilter('30days')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${timeFilter === '30days'
                  ? 'bg-primary text-white'
                  : 'bg-white/5 text-white/60 hover:bg-white/10'
                }`}
            >
              30 Days
            </button>
          </div>
        </div>
      </div>

      {/* Operations Table */}
      <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden shadow-glass">
        {isLoading ? (
          <div className="p-8 text-center text-white/60">
            Loading operations...
          </div>
        ) : operations.length === 0 ? (
          <div className="p-8 text-center">
            <Clock size={48} className="mx-auto text-white/20 mb-3" />
            <p className="text-white/60">No file operations found</p>
            <p className="text-white/40 text-sm mt-1">
              {searchTerm ? 'Try a different search term' : 'Operations will appear here when files are organized'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-white/5 border-b border-white/10">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-white/60 uppercase tracking-wider">Time</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-white/60 uppercase tracking-wider">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-white/60 uppercase tracking-wider">File</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-white/60 uppercase tracking-wider">Location</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-white/60 uppercase tracking-wider">Confidence</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-white/60 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-white/60 uppercase tracking-wider">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {operations.map((op) => (
                  <tr key={op.operation_id} className="hover:bg-white/5 transition-colors">
                    <td className="px-4 py-3 text-sm text-white/80">
                      {formatTimestamp(op.timestamp)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${op.operation_type === 'organize' ? 'bg-primary/20 text-primary' :
                          op.operation_type === 'rename' ? 'bg-warning/20 text-warning' :
                            'bg-white/10 text-white/60'
                        }`}>
                        {op.operation_type}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-start gap-2">
                        <FileText size={16} className="text-white/40 mt-0.5 flex-shrink-0" />
                        <div className="min-w-0">
                          <div className="text-sm text-white font-medium truncate">{op.new_filename}</div>
                          {op.original_filename !== op.new_filename && (
                            <div className="text-xs text-white/40 truncate">was: {op.original_filename}</div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-start gap-2">
                        <FolderOpen size={16} className="text-white/40 mt-0.5 flex-shrink-0" />
                        <div className="min-w-0">
                          <div className="text-sm text-white/80 truncate max-w-xs" title={op.new_location}>
                            {op.new_location.split('/').slice(-2).join('/')}
                          </div>
                          {op.google_drive_id && (
                            <div className="text-xs text-blue-400">Google Drive</div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-2 bg-white/10 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${op.confidence >= 0.85 ? 'bg-success' :
                                op.confidence >= 0.7 ? 'bg-warning' :
                                  'bg-destructive'
                              }`}
                            style={{ width: `${op.confidence * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-white/60">{Math.round(op.confidence * 100)}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${op.status === 'active' ? 'bg-success/20 text-success' :
                          op.status === 'undone' ? 'bg-white/10 text-white/60' :
                            'bg-destructive/20 text-destructive'
                        }`}>
                        {op.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {op.status === 'active' ? (
                        <button
                          onClick={() => {
                            if (window.confirm(`Undo "${op.new_filename}"?`)) {
                              undoMutation.mutate(op.operation_id)
                            }
                          }}
                          disabled={undoMutation.isPending}
                          className="inline-flex items-center gap-1 px-3 py-1.5 bg-primary/20 hover:bg-primary/30 border border-primary/30 rounded-lg text-xs font-medium text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <Undo2 size={14} />
                          Undo
                        </button>
                      ) : (
                        <span className="text-xs text-white/40">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Stats Footer */}
      {operations.length > 0 && (
        <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-4 shadow-glass">
          <div className="flex items-center justify-between text-sm">
            <div className="text-white/60">
              Showing <span className="text-white font-medium">{operations.length}</span> operations
            </div>
            <div className="text-white/60">
              {operations.filter(op => op.status === 'active').length} active • {operations.filter(op => op.status === 'undone').length} undone
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
