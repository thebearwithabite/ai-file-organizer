import { useState, useEffect } from 'react'
import { Copy, Trash2, FileCheck, AlertCircle, FolderOpen, HardDrive, CheckCircle2, Info } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '../services/api'
import type { DuplicateGroup, SystemStatus } from '../types/api'
import { formatPath } from '../lib/utils'
import { useQuery } from '@tanstack/react-query'


export default function Duplicates() {
  const [duplicateGroups, setDuplicateGroups] = useState<DuplicateGroup[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isScanning, setIsScanning] = useState(false)
  const [selectedKeepIndex, setSelectedKeepIndex] = useState<Record<string, number>>({})
  const [confirmingGroupId, setConfirmingGroupId] = useState<string | null>(null)
  const [cleaningGroupId, setCleaningGroupId] = useState<string | null>(null)

  const { data: status } = useQuery<SystemStatus>({
    queryKey: ['system-status'],
    queryFn: api.getSystemStatus,
  })
  const driveRoot = status?.google_drive?.drive_root


  // Fetch duplicates on mount
  useEffect(() => {
    fetchDuplicates()
  }, [])

  const fetchDuplicates = async () => {
    try {
      setIsLoading(true)
      setIsScanning(true)
      const response = await api.getDuplicates()
      setDuplicateGroups(response.groups)

      // Initialize selected keep index for each group (default to first file)
      const initialSelections: Record<string, number> = {}
      response.groups.forEach(group => {
        initialSelections[group.group_id] = 0
      })
      setSelectedKeepIndex(initialSelections)

      if (response.groups.length === 0) {
        toast.success('No duplicates found', {
          description: 'Your file system is clean!',
        })
      } else {
        toast.info(`Found ${response.groups.length} duplicate groups`, {
          description: 'Review and clean up duplicates',
        })
      }
    } catch (error) {
      console.error('Error fetching duplicates:', error)
      toast.error('Failed to scan for duplicates')
    } finally {
      setIsLoading(false)
      setIsScanning(false)
    }
  }

  const handleCleanDuplicates = async (groupId: string) => {
    const keepIndex = selectedKeepIndex[groupId]
    if (keepIndex === undefined) return

    try {
      setCleaningGroupId(groupId)
      await api.cleanDuplicates(groupId, keepIndex)

      const group = duplicateGroups.find(g => g.group_id === groupId)
      const spaceSaved = group ? group.total_size - group.files[keepIndex].size : 0

      toast.success('Duplicates cleaned successfully', {
        description: `Freed ${(spaceSaved / (1024 * 1024)).toFixed(2)} MB. Operation can be undone in Settings → Rollback.`,
        duration: 5000,
      })

      // Remove the group from the list
      setDuplicateGroups(prev => prev.filter(g => g.group_id !== groupId))
      setConfirmingGroupId(null)
    } catch (error) {
      console.error('Error cleaning duplicates:', error)
      toast.error('Failed to clean duplicates')
    } finally {
      setCleaningGroupId(null)
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getTotalDuplicateSize = (): number => {
    return duplicateGroups.reduce((total, group) => {
      // Size savings = total size - size of one file
      return total + (group.total_size - (group.files[0]?.size || 0))
    }, 0)
  }

  const getFileName = (path: string): string => {
    return path.split('/').pop() || path
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-white">Duplicate Files</h1>
        <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-12 shadow-glass">
          <div className="flex flex-col items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"></div>
            <div className="text-white/60">Scanning for duplicate files...</div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Duplicate Files</h1>
          <p className="text-white/60 mt-1">
            Review and clean up duplicate files to free up disk space
          </p>
        </div>
        <button
          onClick={fetchDuplicates}
          disabled={isScanning}
          className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/80 rounded-lg text-sm font-medium text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Copy size={16} />
          {isScanning ? 'Scanning...' : 'Rescan'}
        </button>
      </div>

      {/* Summary Stats */}
      {duplicateGroups.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass">
            <div className="flex items-center gap-3 mb-2">
              <Copy size={20} className="text-cyan-400" />
              <div className="text-xs text-white/60">Duplicate Groups</div>
            </div>
            <div className="text-3xl font-bold text-white">{duplicateGroups.length}</div>
          </div>

          <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass">
            <div className="flex items-center gap-3 mb-2">
              <FileCheck size={20} className="text-purple-400" />
              <div className="text-xs text-white/60">Total Files</div>
            </div>
            <div className="text-3xl font-bold text-white">
              {duplicateGroups.reduce((total, group) => total + group.files.length, 0)}
            </div>
          </div>

          <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass">
            <div className="flex items-center gap-3 mb-2">
              <HardDrive size={20} className="text-success" />
              <div className="text-xs text-white/60">Potential Savings</div>
            </div>
            <div className="text-3xl font-bold text-white">
              {formatFileSize(getTotalDuplicateSize())}
            </div>
          </div>
        </div>
      )}

      {/* Duplicate Groups List */}
      {duplicateGroups.length === 0 ? (
        <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-12 shadow-glass text-center">
          <CheckCircle2 size={48} className="mx-auto text-success mb-4" />
          <div className="text-xl font-semibold text-white mb-2">No Duplicates Found</div>
          <div className="text-white/60">Your file system is clean and organized!</div>
        </div>
      ) : (
        <div className="space-y-4">
          {duplicateGroups.map((group) => (
            <div
              key={group.group_id}
              className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass animate-fade-in"
            >
              {/* Group Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-warning/20 rounded-lg">
                    <AlertCircle size={20} className="text-warning" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white">
                      {group.files.length} identical files
                    </div>
                    <div className="text-xs text-white/60">
                      Total size: {formatFileSize(group.total_size)} • Can free: {formatFileSize(group.total_size - (group.files[0]?.size || 0))}
                    </div>
                  </div>
                </div>
                <div className="group relative">
                  <Info size={16} className="text-white/40 hover:text-white/60 cursor-help transition-colors" />
                  <div className="invisible group-hover:visible absolute right-0 top-6 w-64 p-3 bg-black/90 backdrop-blur-xl border border-white/20 rounded-lg text-xs text-white/80 z-10 shadow-xl">
                    Select which file to keep, then clean the rest. All operations can be undone via Settings → Rollback.
                  </div>
                </div>
              </div>

              {/* File List */}
              <div className="space-y-2 mb-4">
                {group.files.map((file, index) => (
                  <div
                    key={index}
                    className={`p-3 rounded-lg border-2 transition-all cursor-pointer ${selectedKeepIndex[group.group_id] === index
                        ? 'bg-primary/20 border-primary/40'
                        : 'bg-white/5 border-white/10 hover:bg-white/10 hover:border-white/20'
                      }`}
                    onClick={() => setSelectedKeepIndex({ ...selectedKeepIndex, [group.group_id]: index })}
                  >
                    <div className="flex items-start gap-3">
                      <input
                        type="radio"
                        checked={selectedKeepIndex[group.group_id] === index}
                        onChange={() => setSelectedKeepIndex({ ...selectedKeepIndex, [group.group_id]: index })}
                        className="mt-1"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <FolderOpen size={14} className="text-white/60 flex-shrink-0" />
                          <div className="text-sm font-medium text-white truncate">
                            {getFileName(file.path)}
                          </div>
                          {selectedKeepIndex[group.group_id] === index && (
                            <span className="px-2 py-0.5 bg-primary/30 text-primary text-xs font-semibold rounded">
                              KEEP
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-white/40 font-mono truncate">
                          {formatPath(file.path, driveRoot)}
                        </div>

                        <div className="flex items-center gap-3 mt-1 text-xs text-white/60">
                          <span>{formatFileSize(file.size)}</span>
                          <span>•</span>
                          <span>{formatDate(file.modified)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Action Buttons */}
              {confirmingGroupId === group.group_id ? (
                <div className="flex gap-2">
                  <button
                    onClick={() => handleCleanDuplicates(group.group_id)}
                    disabled={cleaningGroupId === group.group_id}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-destructive hover:bg-destructive/80 rounded-lg text-sm font-medium text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <CheckCircle2 size={16} />
                    {cleaningGroupId === group.group_id ? 'Cleaning...' : 'Confirm Clean'}
                  </button>
                  <button
                    onClick={() => setConfirmingGroupId(null)}
                    disabled={cleaningGroupId === group.group_id}
                    className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm font-medium text-white transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmingGroupId(group.group_id)}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-warning hover:bg-warning/80 rounded-lg text-sm font-medium text-black transition-colors"
                >
                  <Trash2 size={16} />
                  Clean Duplicates (Keep Selected)
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Info Box */}
      <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-4 shadow-glass">
        <div className="flex items-start gap-3">
          <Info size={20} className="text-primary flex-shrink-0 mt-0.5" />
          <div className="text-sm text-white/70">
            <strong className="text-white">How it works:</strong> Duplicates are identified by identical file content (SHA-256 hash).
            Select which copy to keep, and the others will be safely moved to the rollback system.
            You can undo any operation from Settings → Rollback.
          </div>
        </div>
      </div>
    </div>
  )
}
