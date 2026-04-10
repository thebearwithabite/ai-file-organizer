import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search as SearchIcon, FileText, FolderOpen, ExternalLink, Loader2, Sparkles } from 'lucide-react'
import { api } from '../services/api'
import { toast } from 'sonner'
import { formatPath } from '../lib/utils'
import type { SystemStatus } from '../types/api'


interface SearchResult {
  file_id: string
  filename: string
  relevance_score: number
  matching_content: string
  file_category: string
  file_size: number
  last_modified: string
  local_path: string
  drive_path: string
  availability: string
  can_stream: boolean
  sync_status: string
  reasoning: string[]
}

export default function Search() {
  const [query, setQuery] = useState('')
  const [searchQuery, setSearchQuery] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['search', searchQuery],
    queryFn: () => api.searchFiles(searchQuery),
    enabled: searchQuery.length > 0,
  })

  const { data: status } = useQuery<SystemStatus>({
    queryKey: ['system-status'],
    queryFn: api.getSystemStatus,
  })
  const driveRoot = status?.google_drive?.drive_root


  const results: SearchResult[] = data?.results || []

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim().length > 0) {
      setSearchQuery(query.trim())
    }
  }

  const handleOpenFile = async (filePath: string) => {
    try {
      await api.openFile(filePath)
      toast.success('Opening file...')
    } catch (error: any) {
      toast.error('Failed to open file', {
        description: error.message,
      })
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const formatDate = (dateString: string) => {
    if (!dateString) return 'Unknown'
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      entertainment: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
      financial: 'bg-green-500/20 text-green-300 border-green-500/30',
      creative: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
      development: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
      audio: 'bg-pink-500/20 text-pink-300 border-pink-500/30',
      image: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
      text_document: 'bg-gray-500/20 text-gray-300 border-gray-500/30',
    }
    return colors[category] || 'bg-white/10 text-white/60 border-white/20'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Search</h1>
        <p className="text-white/60 mt-1">Find files using natural language and semantic understanding</p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="relative">
        <div className="relative">
          <SearchIcon className="absolute left-4 top-1/2 transform -translate-y-1/2 text-white/40" size={20} />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search for files... (e.g., 'Client Name contracts', 'creative project audio', 'payment terms')"
            className="w-full pl-12 pr-4 py-4 bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-primary/50 shadow-glass"
          />
        </div>
        <button
          type="submit"
          disabled={query.trim().length === 0}
          className="absolute right-2 top-1/2 transform -translate-y-1/2 px-6 py-2 bg-primary hover:bg-primary/90 rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Search
        </button>
      </form>

      {/* Example Queries */}
      {!searchQuery && (
        <div className="bg-white/[0.05] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles size={20} className="text-primary" />
            <h3 className="text-sm font-medium text-white">Try these searches:</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {[
              'Client Name contracts',
              'creative project audio',
              'payment terms',
              'VEO prompts',
              'episode scripts',
              'client agreements',
            ].map((example) => (
              <button
                key={example}
                onClick={() => {
                  setQuery(example)
                  setSearchQuery(example)
                }}
                className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white/80 hover:text-white transition-colors"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-12 text-center shadow-glass">
          <Loader2 size={48} className="mx-auto text-primary mb-4 animate-spin" />
          <p className="text-white/80 font-medium">Searching...</p>
          <p className="text-white/40 text-sm mt-2">Looking through Google Drive and local files</p>
        </div>
      )}

      {/* Results */}
      {searchQuery && !isLoading && (
        <>
          {/* Results Header */}
          <div className="flex items-center justify-between">
            <div className="text-white/80">
              Found <span className="font-bold text-white">{results.length}</span> result{results.length !== 1 ? 's' : ''} for{' '}
              <span className="font-bold text-primary">"{searchQuery}"</span>
            </div>
          </div>

          {/* Results List */}
          {results.length === 0 ? (
            <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-12 text-center shadow-glass">
              <SearchIcon size={48} className="mx-auto text-white/40 mb-4" />
              <p className="text-white/80 font-medium mb-2">No results found</p>
              <p className="text-white/60 text-sm">Try a different search query or check your spelling</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {results.map((result) => (
                <div
                  key={result.file_id}
                  className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass hover:bg-white/[0.09] transition-colors"
                >
                  <div className="flex items-start gap-4">
                    {/* File Icon */}
                    <div className="p-4 bg-white/10 rounded-xl flex-shrink-0">
                      <FileText size={32} className="text-blue-400" />
                    </div>

                    {/* File Info */}
                    <div className="flex-1 min-w-0">
                      {/* Filename & Category */}
                      <div className="flex items-start justify-between gap-4 mb-2">
                        <h3 className="text-lg font-semibold text-white truncate">{result.filename}</h3>
                        <span className={`px-3 py-1 rounded-lg text-xs font-medium border ${getCategoryColor(result.file_category)}`}>
                          {result.file_category.replace('_', ' ')}
                        </span>
                      </div>

                      {/* Matching Content */}
                      {result.matching_content && (
                        <div className="mb-3 p-3 bg-white/5 border border-white/10 rounded-lg">
                          <p className="text-sm text-white/70 line-clamp-2">{result.matching_content}</p>
                        </div>
                      )}

                      {/* Reasoning */}
                      {result.reasoning && result.reasoning.length > 0 && (
                        <div className="mb-3">
                          <div className="text-xs text-white/50 mb-1">Why this matches:</div>
                          <div className="flex flex-wrap gap-2">
                            {result.reasoning.slice(0, 3).map((reason, idx) => (
                              <span key={idx} className="text-xs px-2 py-1 bg-primary/20 text-primary rounded">
                                {reason}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Metadata */}
                      <div className="flex items-center gap-4 text-xs text-white/50 mb-3">
                        <span>Relevance: {Math.round(result.relevance_score * 100)}%</span>
                        <span>•</span>
                        <span>{formatFileSize(result.file_size)}</span>
                        <span>•</span>
                        <span>{formatDate(result.last_modified)}</span>
                        <span>•</span>
                        <span className="capitalize">{result.availability}</span>
                      </div>

                      {/* File Path */}
                      <div className="text-xs text-white/40 mb-3 truncate">
                        {formatPath(result.local_path || result.drive_path, driveRoot) || 'Path not available'}
                      </div>


                      {/* Actions */}
                      <div className="flex gap-3">
                        <button
                          onClick={() => handleOpenFile(result.local_path || result.drive_path)}
                          className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 rounded-xl text-sm font-medium transition-colors"
                        >
                          <ExternalLink size={16} />
                          Open File
                        </button>
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(result.local_path || result.drive_path)
                            toast.success('Path copied to clipboard')
                          }}
                          className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-xl text-sm transition-colors"
                        >
                          <FolderOpen size={16} />
                          Copy Path
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
