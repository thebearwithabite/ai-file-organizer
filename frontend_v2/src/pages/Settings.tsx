import { useState, useEffect } from 'react'
import { Plus, FolderOpen, Trash2, Edit2, Save, X, Brain, Target, TrendingUp, Image, Video, Music, FileText, Award } from 'lucide-react'
import { toast } from 'sonner'

interface Category {
  id: string
  name: string
  path: string
  color: string
  description: string
}

interface LearningStats {
  total_learning_events: number
  image_events: number
  video_events: number
  audio_events: number
  document_events: number
  unique_categories_learned: number
  most_common_category: string | null
  top_confidence_average: number
  media_type_breakdown: Record<string, number>
  category_distribution: Record<string, number>
}

export default function Settings() {
  const [categories, setCategories] = useState<Category[]>([
    { id: '1', name: 'Entertainment', path: '01_ACTIVE_PROJECTS/Entertainment_Industry', color: 'bg-purple-500', description: 'Industry contracts and talent management' },
    { id: '2', name: 'Financial', path: '01_ACTIVE_PROJECTS/Business_Operations/Financial_Records', color: 'bg-green-500', description: 'Invoices, tax records, and commissions' },
    { id: '3', name: 'Creative', path: '01_ACTIVE_PROJECTS/Creative_Projects', color: 'bg-blue-500', description: 'Scripts, audio, and creative content' },
    { id: '4', name: 'Development', path: '01_ACTIVE_PROJECTS/Development_Projects', color: 'bg-orange-500', description: 'Code projects and technical work' },
    { id: '5', name: 'Audio', path: '01_ACTIVE_PROJECTS/Creative_Projects/Audio_Content', color: 'bg-pink-500', description: 'Music, podcasts, and audio files' },
    { id: '6', name: 'Images', path: '01_ACTIVE_PROJECTS/Creative_Projects/Visual_Content', color: 'bg-cyan-500', description: 'Photos, designs, and visual assets' },
    { id: '7', name: 'Documents', path: '02_REFERENCE/Documents', color: 'bg-gray-500', description: 'General reference documents' },
  ])

  const [isAddingCategory, setIsAddingCategory] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [newCategory, setNewCategory] = useState({ name: '', path: '', color: 'bg-indigo-500', description: '' })

  // Learning statistics state
  const [learningStats, setLearningStats] = useState<LearningStats | null>(null)
  const [isLoadingStats, setIsLoadingStats] = useState(true)

  const colorOptions = [
    'bg-red-500', 'bg-orange-500', 'bg-amber-500', 'bg-yellow-500',
    'bg-lime-500', 'bg-green-500', 'bg-emerald-500', 'bg-teal-500',
    'bg-cyan-500', 'bg-sky-500', 'bg-blue-500', 'bg-indigo-500',
    'bg-violet-500', 'bg-purple-500', 'bg-fuchsia-500', 'bg-pink-500',
    'bg-rose-500', 'bg-gray-500'
  ]

  // Fetch learning statistics on component mount
  useEffect(() => {
    const fetchLearningStats = async () => {
      try {
        setIsLoadingStats(true)
        const response = await fetch('http://localhost:8000/api/settings/learning-stats')
        if (!response.ok) {
          throw new Error('Failed to fetch learning statistics')
        }
        const data = await response.json()
        setLearningStats(data)
      } catch (error) {
        console.error('Error fetching learning stats:', error)
        toast.error('Failed to load learning statistics')
      } finally {
        setIsLoadingStats(false)
      }
    }

    fetchLearningStats()
  }, [])

  // Helper function to format numbers with thousands separators
  const formatNumber = (num: number): string => {
    return num.toLocaleString('en-US')
  }

  const handleAddCategory = () => {
    if (!newCategory.name || !newCategory.path) {
      toast.error('Name and path are required')
      return
    }

    const category: Category = {
      id: Date.now().toString(),
      ...newCategory
    }

    setCategories([...categories, category])
    setNewCategory({ name: '', path: '', color: 'bg-indigo-500', description: '' })
    setIsAddingCategory(false)
    toast.success('Category added! The AI will start learning from your file placements.')
  }

  const handleDeleteCategory = (id: string) => {
    if (window.confirm('Delete this category? Files in this category will not be moved.')) {
      setCategories(categories.filter(c => c.id !== id))
      toast.success('Category deleted')
    }
  }

  const handleSaveEdit = (id: string, updates: Partial<Category>) => {
    setCategories(categories.map(c => c.id === id ? { ...c, ...updates } : c))
    setEditingId(null)
    toast.success('Category updated')
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="text-white/60 mt-1">Configure categories and learning preferences</p>
      </div>

      {/* Learning Statistics */}
      <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass animate-fade-in">
        <div className="flex items-center gap-2 mb-4">
          <Brain size={20} className="text-primary" />
          <h2 className="text-xl font-semibold text-white">Learning Statistics</h2>
        </div>

        {isLoadingStats ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : learningStats && learningStats.total_learning_events > 0 ? (
          <>
            {/* Main Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-white/5 rounded-lg p-4 animate-fade-in">
                <div className="flex items-center gap-2 mb-2">
                  <Target size={16} className="text-success" />
                  <div className="text-sm text-white/60">Total Learning Events</div>
                </div>
                <div className="text-3xl font-bold text-white">{formatNumber(learningStats.total_learning_events)}</div>
                <div className="text-xs text-white/40 mt-1">AI classifications tracked</div>
              </div>

              <div className="bg-white/5 rounded-lg p-4 animate-fade-in" style={{ animationDelay: '100ms' }}>
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp size={16} className="text-primary" />
                  <div className="text-sm text-white/60">Unique Categories</div>
                </div>
                <div className="text-3xl font-bold text-white">{formatNumber(learningStats.unique_categories_learned)}</div>
                <div className="text-xs text-white/40 mt-1">Patterns discovered</div>
              </div>

              <div className="bg-white/5 rounded-lg p-4 animate-fade-in" style={{ animationDelay: '200ms' }}>
                <div className="flex items-center gap-2 mb-2">
                  <Award size={16} className="text-warning" />
                  <div className="text-sm text-white/60">Top Confidence</div>
                </div>
                <div className="text-3xl font-bold text-white">{(learningStats.top_confidence_average * 100).toFixed(0)}%</div>
                <div className="text-xs text-white/40 mt-1">Average of top 10 events</div>
                {/* Progress bar */}
                <div className="mt-2 h-1.5 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-warning to-success transition-all duration-1000 ease-out"
                    style={{ width: `${learningStats.top_confidence_average * 100}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Media Type Breakdown */}
            <div className="mb-6">
              <div className="text-sm font-medium text-white/80 mb-3">Media Type Breakdown</div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-white/5 rounded-lg p-3 flex items-center gap-3">
                  <div className="p-2 bg-cyan-500/20 rounded-lg">
                    <Image size={16} className="text-cyan-400" />
                  </div>
                  <div>
                    <div className="text-xs text-white/60">Images</div>
                    <div className="text-lg font-bold text-white">{formatNumber(learningStats.image_events)}</div>
                  </div>
                </div>

                <div className="bg-white/5 rounded-lg p-3 flex items-center gap-3">
                  <div className="p-2 bg-purple-500/20 rounded-lg">
                    <Video size={16} className="text-purple-400" />
                  </div>
                  <div>
                    <div className="text-xs text-white/60">Videos</div>
                    <div className="text-lg font-bold text-white">{formatNumber(learningStats.video_events)}</div>
                  </div>
                </div>

                <div className="bg-white/5 rounded-lg p-3 flex items-center gap-3">
                  <div className="p-2 bg-pink-500/20 rounded-lg">
                    <Music size={16} className="text-pink-400" />
                  </div>
                  <div>
                    <div className="text-xs text-white/60">Audio</div>
                    <div className="text-lg font-bold text-white">{formatNumber(learningStats.audio_events)}</div>
                  </div>
                </div>

                <div className="bg-white/5 rounded-lg p-3 flex items-center gap-3">
                  <div className="p-2 bg-green-500/20 rounded-lg">
                    <FileText size={16} className="text-green-400" />
                  </div>
                  <div>
                    <div className="text-xs text-white/60">Documents</div>
                    <div className="text-lg font-bold text-white">{formatNumber(learningStats.document_events)}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Most Common Category */}
            {learningStats.most_common_category && (
              <div className="mt-4 p-3 bg-primary/10 border border-primary/20 rounded-lg">
                <div className="text-sm text-primary">
                  <strong>Most Common Category:</strong> {learningStats.most_common_category}
                  {learningStats.category_distribution[learningStats.most_common_category] &&
                    ` (${formatNumber(learningStats.category_distribution[learningStats.most_common_category])} files)`
                  }
                </div>
              </div>
            )}

            <div className="mt-4 p-3 bg-success/10 border border-success/20 rounded-lg">
              <div className="text-sm text-success">
                <strong>Adaptive Learning Active:</strong> The system is continuously learning from your file movements and classifications.
              </div>
            </div>
          </>
        ) : (
          <div className="py-12 text-center">
            <Brain size={48} className="mx-auto text-white/20 mb-4" />
            <div className="text-white/60 text-lg font-medium mb-2">No learning events recorded yet</div>
            <div className="text-white/40 text-sm max-w-md mx-auto">
              Start organizing files to help the AI learn your preferences. The system will track classifications and improve over time.
            </div>
          </div>
        )}
      </div>

      {/* Category Management */}
      <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <FolderOpen size={20} className="text-primary" />
            <h2 className="text-xl font-semibold text-white">Category Management</h2>
          </div>
          <button
            onClick={() => setIsAddingCategory(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/80 rounded-lg text-sm font-medium text-white transition-colors"
          >
            <Plus size={16} />
            Add Category
          </button>
        </div>

        {/* Add Category Form */}
        {isAddingCategory && (
          <div className="mb-6 p-4 bg-white/5 border border-white/10 rounded-lg">
            <h3 className="text-sm font-medium text-white mb-4">New Category</h3>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Category name (e.g., Client Contracts)"
                value={newCategory.name}
                onChange={(e) => setNewCategory({ ...newCategory, name: e.target.value })}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <input
                type="text"
                placeholder="Folder path (e.g., 01_ACTIVE_PROJECTS/Clients)"
                value={newCategory.path}
                onChange={(e) => setNewCategory({ ...newCategory, path: e.target.value })}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <input
                type="text"
                placeholder="Description (optional)"
                value={newCategory.description}
                onChange={(e) => setNewCategory({ ...newCategory, description: e.target.value })}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              
              <div>
                <div className="text-xs text-white/60 mb-2">Color</div>
                <div className="flex flex-wrap gap-2">
                  {colorOptions.map(color => (
                    <button
                      key={color}
                      onClick={() => setNewCategory({ ...newCategory, color })}
                      className={`w-8 h-8 rounded-lg ${color} ${newCategory.color === color ? 'ring-2 ring-white' : ''}`}
                    />
                  ))}
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={handleAddCategory}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-success hover:bg-success/80 rounded-lg text-sm font-medium text-white transition-colors"
                >
                  <Save size={16} />
                  Save Category
                </button>
                <button
                  onClick={() => {
                    setIsAddingCategory(false)
                    setNewCategory({ name: '', path: '', color: 'bg-indigo-500', description: '' })
                  }}
                  className="px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-sm font-medium text-white transition-colors"
                >
                  <X size={16} />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Category List */}
        <div className="space-y-3">
          {categories.map(category => (
            <div key={category.id} className="flex items-center gap-4 p-4 bg-white/5 rounded-lg hover:bg-white/[0.07] transition-colors">
              <div className={`w-3 h-3 rounded-full ${category.color}`} />
              
              {editingId === category.id ? (
                <div className="flex-1 space-y-2">
                  <input
                    type="text"
                    defaultValue={category.name}
                    onBlur={(e) => handleSaveEdit(category.id, { name: e.target.value })}
                    className="w-full px-2 py-1 bg-white/10 border border-white/10 rounded text-white text-sm"
                  />
                  <input
                    type="text"
                    defaultValue={category.path}
                    onBlur={(e) => handleSaveEdit(category.id, { path: e.target.value })}
                    className="w-full px-2 py-1 bg-white/10 border border-white/10 rounded text-white text-xs font-mono"
                  />
                </div>
              ) : (
                <div className="flex-1">
                  <div className="text-sm font-medium text-white">{category.name}</div>
                  <div className="text-xs text-white/40 font-mono">{category.path}</div>
                  {category.description && (
                    <div className="text-xs text-white/60 mt-1">{category.description}</div>
                  )}
                </div>
              )}

              <div className="flex items-center gap-2">
                {editingId === category.id ? (
                  <button
                    onClick={() => setEditingId(null)}
                    className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                  >
                    <Save size={16} className="text-success" />
                  </button>
                ) : (
                  <button
                    onClick={() => setEditingId(category.id)}
                    className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                  >
                    <Edit2 size={16} className="text-white/60" />
                  </button>
                )}
                <button
                  onClick={() => handleDeleteCategory(category.id)}
                  className="p-2 hover:bg-destructive/20 rounded-lg transition-colors"
                >
                  <Trash2 size={16} className="text-destructive" />
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 p-3 bg-white/5 rounded-lg">
          <div className="text-xs text-white/60">
            <strong>How it works:</strong> When you add a new category, the AI will start recognizing similar files. 
            The more you use it, the better it gets at auto-classifying to your custom categories.
          </div>
        </div>
      </div>
    </div>
  )
}
