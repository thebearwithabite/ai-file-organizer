import { useState, useEffect } from 'react'
import { RotateCcw, Trash2, FolderOpen, CheckCircle2, Info, Search as SearchIcon } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '../../services/api'
import type { RollbackOperation } from '../../types/api'

export default function RollbackPanel() {
  const [operations, setOperations] = useState<RollbackOperation[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [undoingId, setUndoingId] = useState<number | null>(null)
  const [undoingToday, setUndoingToday] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [confirmUndoAll, setConfirmUndoAll] = useState(false)

  // Fetch rollback operations
  const fetchOperations = async () => {
    try {
      setIsLoading(true)
      const response = await api.getRollbackOperations({ days: 30 })
      setOperations(response.data?.operations || [])
    } catch (error) {
      console.error('Error fetching rollback operations:', error)
      toast.error('Failed to load rollback history')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchOperations()
  }, [])

  const handleUndoOperation = async (operationId: number) => {
    try {
      setUndoingId(operationId)
      await api.undoOperation(operationId)

      toast.success('Operation undone successfully', {
        description: `File restored to original location`,
        duration: 4000,
      })

      // Refresh operations list
      await fetchOperations()
    } catch (error: any) {
      console.error('Error undoing operation:', error)
      toast.error(error.message || 'Failed to undo operation')
    } finally {
      setUndoingId(null)
    }
  }

  const handleUndoAllToday = async () => {
    if (!confirmUndoAll) {
      setConfirmUndoAll(true)
      return
    }

    try {
      setUndoingToday(true)
      const result = await api.undoToday()

      toast.success('All today\'s operations undone', {
        description: `${result.count || 0} files restored to original locations`,
        duration: 4000,
      })

      // Refresh operations list
      await fetchOperations()
      setConfirmUndoAll(false)
    } catch (error: any) {
      console.error('Error undoing today\'s operations:', error)
      toast.error(error.message || 'Failed to undo today\'s operations')
    } finally {
      setUndoingToday(false)
    }
  }

  const formatTimestamp = (timestamp: string): string => {
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

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    })
  }

  const getOperationIcon = (operationType: string) => {
    switch (operationType.toLowerCase()) {
      case 'move':
        return <FolderOpen size={16} className="text-blue-400" />
      case 'delete':
        return <Trash2 size={16} className="text-red-400" />
      case 'rename':
        return <RotateCcw size={16} className="text-purple-400" />
      default:
        return <FolderOpen size={16} className="text-white/60" />
    }
  }

  // Filter operations based on search query
  const filteredOperations = operations.filter(op => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      op.original_filename.toLowerCase().includes(query) ||
      op.new_filename.toLowerCase().includes(query) ||
      op.original_path.toLowerCase().includes(query) ||
      op.new_location.toLowerCase().includes(query)
    )
  })

  // Get today's operations count
  const todayOperations = operations.filter(op => {
    const opDate = new Date(op.timestamp)
    const today = new Date()
    return opDate.toDateString() === today.toDateString()
  })

  if (isLoading) {
    return (
      <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass animate-fade-in">
      <div className="flex items-center gap-2 mb-4">
        <RotateCcw size={20} className="text-warning" />
        <h2 className="text-xl font-semibold text-white">Rollback History</h2>
        <div className="group relative ml-auto">
          <Info size={16} className="text-white/40 hover:text-white/60 cursor-help transition-colors" />
          <div className="invisible group-hover:visible absolute right-0 top-6 w-72 p-3 bg-black/90 backdrop-blur-xl border border-white/20 rounded-lg text-xs text-white/80 z-10 shadow-xl">
            Complete safety net for all file operations. Every move, rename, or deletion can be undone. ADHD-friendly: eliminates anxiety about making mistakes.
          </div>
        </div>
      </div>

      <p className="text-white/60 text-sm mb-4">
        View and undo recent file operations (last 30 days)
      </p>

      {/* Search and Actions */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <div className="flex-1 relative">
          <SearchIcon size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" />
          <input
            type="text"
            placeholder="Search by filename or path..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm"
          />
        </div>
        {todayOperations.length > 0 && (
          confirmUndoAll ? (
            <div className="flex gap-2">
              <button
                onClick={handleUndoAllToday}
                disabled={undoingToday}
                className="px-4 py-2 bg-destructive hover:bg-destructive/80 rounded-lg text-sm font-medium text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {undoingToday ? 'Undoing...' : 'Confirm Undo All'}
              </button>
              <button
                onClick={() => setConfirmUndoAll(false)}
                disabled={undoingToday}
                className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm font-medium text-white transition-colors"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirmUndoAll(true)}
              className="px-4 py-2 bg-warning hover:bg-warning/80 rounded-lg text-sm font-medium text-black transition-colors whitespace-nowrap"
            >
              Undo All Today ({todayOperations.length})
            </button>
          )
        )}
      </div>

      {/* Operations Table */}
      {filteredOperations.length === 0 ? (
        <div className="py-12 text-center">
          <CheckCircle2 size={48} className="mx-auto text-white/20 mb-4" />
          <div className="text-white/60 text-lg font-medium mb-2">
            {searchQuery ? 'No matching operations found' : 'No operations recorded'}
          </div>
          <div className="text-white/40 text-sm max-w-md mx-auto">
            {searchQuery
              ? 'Try a different search term'
              : 'File operations will appear here as you organize files'}
          </div>
        </div>
      ) : (
        <div className="space-y-2 max-h-[600px] overflow-y-auto">
          {filteredOperations.slice(0, 50).map((operation) => (
            <div
              key={operation.operation_id}
              className="p-4 bg-white/5 hover:bg-white/[0.07] rounded-lg border border-white/10 transition-colors"
            >
              <div className="flex items-start gap-3">
                <div className="mt-1">
                  {getOperationIcon(operation.operation_type)}
                </div>

                <div className="flex-1 min-w-0">
                  {/* Header */}
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-white capitalize">
                          {operation.operation_type}
                        </span>
                        <span className="px-2 py-0.5 bg-white/10 text-white/60 text-xs rounded">
                          {formatTimestamp(operation.timestamp)}
                        </span>
                        {operation.status === 'undone' && (
                          <span className="px-2 py-0.5 bg-success/20 text-success text-xs font-semibold rounded">
                            UNDONE
                          </span>
                        )}
                      </div>
                      {operation.confidence && (
                        <div className="text-xs text-white/40">
                          Confidence: {(operation.confidence * 100).toFixed(0)}%
                        </div>
                      )}
                    </div>
                  </div>

                  {/* File paths */}
                  <div className="space-y-1 mb-2">
                    <div className="flex items-start gap-2">
                      <span className="text-xs text-white/40 flex-shrink-0">From:</span>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-white/80 font-mono truncate">
                          {operation.original_filename}
                        </div>
                        <div className="text-xs text-white/40 font-mono truncate">
                          {operation.original_path}
                        </div>
                      </div>
                    </div>
                    {operation.new_location && operation.new_location !== operation.original_path && (
                      <div className="flex items-start gap-2">
                        <span className="text-xs text-white/40 flex-shrink-0">To:</span>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-white/80 font-mono truncate">
                            {operation.new_filename}
                          </div>
                          <div className="text-xs text-white/40 font-mono truncate">
                            {operation.new_location}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Notes */}
                  {operation.notes && (
                    <div className="text-xs text-white/60 mb-2 p-2 bg-white/5 rounded">
                      {operation.notes}
                    </div>
                  )}

                  {/* Undo button */}
                  {operation.status !== 'undone' && (
                    <button
                      onClick={() => handleUndoOperation(operation.operation_id)}
                      disabled={undoingId === operation.operation_id}
                      className="flex items-center gap-2 px-3 py-1.5 bg-warning/20 hover:bg-warning/30 border border-warning/30 rounded text-xs font-medium text-warning transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <RotateCcw size={14} />
                      {undoingId === operation.operation_id ? 'Undoing...' : 'Undo Operation'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Footer info */}
      <div className="mt-4 p-3 bg-primary/10 border border-primary/20 rounded-lg">
        <div className="text-xs text-primary">
          <strong>Complete Safety:</strong> All file operations are tracked and can be undone. Files are never permanently deleted - they can always be restored from rollback history.
        </div>
      </div>

      {/* Total operations count */}
      {operations.length > 0 && (
        <div className="mt-2 text-xs text-white/40 text-center">
          Showing {Math.min(filteredOperations.length, 50)} of {filteredOperations.length} operations
          {searchQuery && ` matching "${searchQuery}"`}
        </div>
      )}
    </div>
  )
}
