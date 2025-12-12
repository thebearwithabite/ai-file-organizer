import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, XCircle, RefreshCw, FileText, AlertTriangle, Sparkles, FolderOpen, Clock } from 'lucide-react'
import { api } from '../services/api'
import { toast } from 'sonner'
import FilePreview from '../components/triage/FilePreview'

interface TriageFile {
  file_id: string
  file_name: string
  file_path: string
  classification: {
    category: string
    confidence: number
    reasoning: string
    needs_review: boolean
  }
  status: string
}

export default function Triage() {
  const queryClient = useQueryClient()
  const [selectedCategory, setSelectedCategory] = useState<Record<string, string>>({})
  const [projectInput, setProjectInput] = useState<Record<string, string>>({})
  const [episodeInput, setEpisodeInput] = useState<Record<string, string>>({})
  const [customFolderPath, setCustomFolderPath] = useState('')
  const [recentFolders, setRecentFolders] = useState<string[]>([])
  const [currentScanMode, setCurrentScanMode] = useState<'downloads' | 'custom'>('downloads')

  // Load recent folders from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('recentTriageFolders')
    if (saved) {
      try {
        setRecentFolders(JSON.parse(saved))
      } catch {
        setRecentFolders([])
      }
    }
  }, [])

  // Save recent folders to localStorage whenever they change
  const addRecentFolder = (folderPath: string) => {
    const updated = [folderPath, ...recentFolders.filter(f => f !== folderPath)].slice(0, 5)
    setRecentFolders(updated)
    localStorage.setItem('recentTriageFolders', JSON.stringify(updated))
  }

  const { data, isLoading } = useQuery({
    queryKey: ['triage-files'],
    queryFn: api.getFilesForReview,
    enabled: false, // Don't auto-fetch on page load - only fetch when scan is triggered
  })

  const { data: knownProjects } = useQuery({
    queryKey: ['known-projects'],
    queryFn: api.getKnownProjects,
  })

  const scanMutation = useMutation({
    mutationFn: api.triggerTriageScan,
    onSuccess: (scanResult) => {
      toast.success(`Scan complete! Found ${scanResult.files_found} files for review`)
      setCurrentScanMode('downloads')
      // Update the query cache with the scan results instead of refetching
      queryClient.setQueryData(['triage-files'], scanResult)
    },
    onError: () => {
      toast.error('Failed to trigger scan')
    },
  })

  const scanFolderMutation = useMutation({
    mutationFn: (folderPath: string) => api.scanCustomFolder(folderPath),
    onSuccess: (scanResult) => {
      const folderName = scanResult.folder_scanned?.split('/').pop() || 'folder'
      toast.success(`Scan complete! Found ${scanResult.files_found} files in ${folderName}`)

      // Add to recent folders
      if (scanResult.folder_scanned) {
        addRecentFolder(scanResult.folder_scanned)
      }

      setCurrentScanMode('custom')
      // Update the query cache with the scan results
      queryClient.setQueryData(['triage-files'], scanResult)
    },
    onError: (error: Error) => {
      toast.error('Failed to scan folder', {
        description: error.message,
      })
    },
  })

  const handleScanCustomFolder = () => {
    if (!customFolderPath.trim()) {
      toast.error('Please enter a folder path')
      return
    }
    scanFolderMutation.mutate(customFolderPath.trim())
  }

  const classifyMutation = useMutation({
    mutationFn: ({ filePath, category, project, episode }: {
      filePath: string;
      category: string;
      project?: string;
      episode?: string;
    }) => api.classifyFile(filePath, category, project, episode),
    onSuccess: (_, variables) => {
      toast.success('File organized successfully')

      // Optimistically update the cache to remove the file immediately
      queryClient.setQueryData(['triage-files'], (oldData: any) => {
        if (!oldData) return oldData
        return {
          ...oldData,
          files: oldData.files.filter((f: TriageFile) => f.file_path !== variables.filePath)
        }
      })

      // Still invalidate to ensure consistency with backend
      queryClient.invalidateQueries({ queryKey: ['triage-files'] })
    },
    onError: (error: Error) => {
      toast.error('Failed to organize file', {
        description: error.message,
      })
    },
  })

  const files: TriageFile[] = data?.files || []

  const categories = [
    { value: 'entertainment', label: 'Entertainment', color: 'bg-purple-500' },
    { value: 'financial', label: 'Financial', color: 'bg-green-500' },
    { value: 'creative', label: 'Creative', color: 'bg-blue-500' },
    { value: 'development', label: 'Development', color: 'bg-orange-500' },
    { value: 'audio', label: 'Audio', color: 'bg-pink-500' },
    { value: 'image', label: 'Images', color: 'bg-cyan-500' },
    { value: 'text_document', label: 'Documents', color: 'bg-gray-500' },
  ]

  const handleClassify = (file: TriageFile) => {
    const category = selectedCategory[file.file_id] || file.classification.category
    const project = projectInput[file.file_id] || undefined
    const episode = episodeInput[file.file_id] || undefined

    classifyMutation.mutate({
      filePath: file.file_path,
      category,
      project,
      episode,
    })
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.85) return 'text-success'
    if (confidence >= 0.7) return 'text-warning'
    return 'text-destructive'
  }

  const getConfidenceBg = (confidence: number) => {
    if (confidence >= 0.85) return 'bg-success/20 border-success/30'
    if (confidence >= 0.7) return 'bg-warning/20 border-warning/30'
    return 'bg-destructive/20 border-destructive/30'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Triage Center</h1>
        <p className="text-white/60 mt-1">Review and classify files with low confidence scores</p>
      </div>

      {/* Folder Selector Section */}
      <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-primary/20 rounded-lg">
            <FolderOpen size={20} className="text-primary" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Choose Scan Source</h2>
            <p className="text-sm text-white/60">Scan Downloads or organize any custom folder</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Downloads Scan */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-white">Downloads Folder</span>
              {currentScanMode === 'downloads' && (
                <span className="text-xs px-2 py-1 bg-primary/20 text-primary rounded-full">Active</span>
              )}
            </div>
            <p className="text-xs text-white/50 mb-4">Scan standard staging areas (Downloads, Desktop)</p>
            <button
              onClick={() => scanMutation.mutate()}
              disabled={scanMutation.isPending}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw size={16} className={scanMutation.isPending ? 'animate-spin' : ''} />
              {scanMutation.isPending ? 'Scanning...' : 'Scan Downloads'}
            </button>
          </div>

          {/* Custom Folder Scan */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-white">Custom Folder</span>
              {currentScanMode === 'custom' && (
                <span className="text-xs px-2 py-1 bg-primary/20 text-primary rounded-full">Active</span>
              )}
            </div>
            <div className="space-y-3">
              <input
                type="text"
                value={customFolderPath}
                onChange={(e) => setCustomFolderPath(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleScanCustomFolder()}
                placeholder="/Users/username/Documents/FolderName"
                className="w-full px-3 py-2 bg-white/5 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 placeholder:text-white/30"
              />
              <button
                onClick={handleScanCustomFolder}
                disabled={scanFolderMutation.isPending}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-success hover:bg-success/90 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <FolderOpen size={16} />
                {scanFolderMutation.isPending ? 'Scanning...' : 'Scan Folder'}
              </button>
            </div>
          </div>
        </div>

        {/* Recent Folders */}
        {recentFolders.length > 0 && (
          <div className="mt-4 pt-4 border-t border-white/10">
            <div className="flex items-center gap-2 mb-3">
              <Clock size={14} className="text-white/60" />
              <span className="text-xs font-medium text-white/60">Recent Folders</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {recentFolders.map((folder, index) => (
                <button
                  key={index}
                  onClick={() => {
                    setCustomFolderPath(folder)
                    scanFolderMutation.mutate(folder)
                  }}
                  disabled={scanFolderMutation.isPending}
                  className="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs text-white/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed truncate max-w-xs"
                  title={folder}
                >
                  {folder.split('/').slice(-2).join('/')}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Stats Banner */}
      <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-4 shadow-glass">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-primary/20 rounded-xl">
              <Sparkles size={24} className="text-primary" />
            </div>
            <div>
              <div className="text-sm text-white/60">Files Pending Review</div>
              <div className="text-2xl font-bold text-white">{files.length}</div>
            </div>
          </div>
          {files.length > 0 && (
            <div className="text-sm text-white/60">
              Average confidence: {
                files.length > 0
                  ? Math.round((files.reduce((sum, f) => sum + (f.classification.confidence || 0), 0) / files.length) * 100)
                  : 0
              }%
            </div>
          )}
        </div>
      </div>

      {/* Files List */}
      {isLoading ? (
        <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-12 text-center shadow-glass">
          <RefreshCw size={48} className="mx-auto text-white/40 mb-4 animate-spin" />
          <p className="text-white/60">Loading files...</p>
        </div>
      ) : files.length === 0 ? (
        <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-12 text-center shadow-glass">
          <CheckCircle size={48} className="mx-auto text-success mb-4" />
          <p className="text-white/80 font-medium mb-2">All Caught Up!</p>
          <p className="text-white/60 text-sm">No files need review at the moment.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {files.map((file) => (
            <div
              key={file.file_id}
              className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass hover:bg-white/[0.09] transition-colors"
            >
              <div className="flex items-start gap-4">
                {/* File Icon */}
                <div className="p-4 bg-white/10 rounded-xl flex-shrink-0">
                  <FileText size={32} className="text-blue-400" />
                </div>

                {/* File Info */}
                <div className="flex-1 min-w-0">
                  {/* Filename */}
                  <h3 className="text-lg font-semibold text-white mb-2 truncate">
                    {file.file_name}
                  </h3>

                  {/* File Preview */}
                  <FilePreview filePath={file.file_path} fileName={file.file_name} />

                  {/* AI Analysis */}
                  <div className={`border rounded-xl p-3 mb-4 ${getConfidenceBg(file.classification.confidence)}`}>
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle size={16} className={getConfidenceColor(file.classification.confidence)} />
                      <span className="text-sm font-medium text-white">
                        AI Confidence: {Math.round((file.classification.confidence || 0) * 100)}%
                      </span>
                    </div>
                    <p className="text-sm text-white/80">{file.classification.reasoning}</p>
                  </div>

                  {/* Category Selection */}
                  <div className="mb-4">
                    <label className="text-xs text-white/60 mb-2 block">Select Category</label>
                    <select
                      value={selectedCategory[file.file_id] || file.classification.category}
                      onChange={(e) => setSelectedCategory({ ...selectedCategory, [file.file_id]: e.target.value })}
                      className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
                    >
                      {categories.map((cat) => (
                        <option key={cat.value} value={cat.value} className="bg-gray-900">
                          {cat.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Hierarchical Organization (Optional) */}
                  <div className="mb-4 space-y-3 p-3 bg-white/5 border border-white/10 rounded-xl">
                    <div className="text-xs text-white/60 font-medium mb-2">
                      📁 Hierarchical Organization (Optional)
                    </div>

                    <div>
                      <label className="text-xs text-white/50 mb-1 block">Project Name</label>
                      <input
                        type="text"
                        list={`projects-${file.file_id}`}
                        value={projectInput[file.file_id] || ''}
                        onChange={(e) => setProjectInput({ ...projectInput, [file.file_id]: e.target.value })}
                        placeholder="e.g., The_Papers_That_Dream, VEO_Prompt_Machine"
                        className="w-full px-3 py-2 bg-white/5 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 placeholder:text-white/30"
                      />
                      <datalist id={`projects-${file.file_id}`}>
                        {knownProjects?.projects.map((p) => (
                          <option key={p.id} value={p.name} />
                        ))}
                      </datalist>
                    </div>

                    <div>
                      <label className="text-xs text-white/50 mb-1 block">Episode/Version</label>
                      <input
                        type="text"
                        value={episodeInput[file.file_id] || ''}
                        onChange={(e) => setEpisodeInput({ ...episodeInput, [file.file_id]: e.target.value })}
                        placeholder="e.g., Episode_02_AttentionIsland"
                        className="w-full px-3 py-2 bg-white/5 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 placeholder:text-white/30"
                      />
                    </div>

                    <div className="text-xs text-white/40 italic">
                      Files will be organized into: Project → Episode → Media Type
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-3">
                    <button
                      onClick={() => handleClassify(file)}
                      disabled={classifyMutation.isPending}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-success hover:bg-success/90 rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <CheckCircle size={18} />
                      Confirm & Organize
                    </button>
                    <button
                      onClick={() => toast.info('Skip functionality coming soon')}
                      className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-xl transition-colors"
                    >
                      <XCircle size={18} className="text-white/60" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
