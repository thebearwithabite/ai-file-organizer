import { useState, useEffect } from 'react'
import { Brain, Target, TrendingUp, Image, Video, Music, FileText, Award, Database, HardDrive, Activity } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '../services/api'
import ConfidenceModeSwitcher from '../components/settings/ConfidenceModeSwitcher'
import RollbackPanel from '../components/settings/RollbackPanel'
import { TaxonomySettings } from '../components/settings/TaxonomySettings'
import IdentityManager from '../components/settings/IdentityManager'

import type { LearningStats } from '../types/api'

interface DatabaseStats {
  total_operations: number
  recent_operations: number
  today_operations: number
  rollback_db_size_mb: number
  vector_db_size_mb: number
  total_learning_events_db: number
  recent_learning_events: number
  learning_db_size_mb: number
  total_db_size_mb: number
  avg_operations_per_day: number
  avg_learning_per_day: number
}

export default function Settings() {
  // Learning statistics state
  const [learningStats, setLearningStats] = useState<LearningStats | null>(null)
  const [isLoadingStats, setIsLoadingStats] = useState(true)

  // Database statistics state
  const [databaseStats, setDatabaseStats] = useState<DatabaseStats | null>(null)
  const [isLoadingDbStats, setIsLoadingDbStats] = useState(true)

  // Fetch learning statistics on component mount
  useEffect(() => {
    const fetchLearningStats = async () => {
      try {
        setIsLoadingStats(true)
        const data = await api.getLearningStats()
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

  // Fetch database statistics on component mount
  useEffect(() => {
    const fetchDatabaseStats = async () => {
      try {
        setIsLoadingDbStats(true)
        const data = await api.getDatabaseStats()
        setDatabaseStats(data)
      } catch (error) {
        console.error('Error fetching database stats:', error)
        toast.error('Failed to load database statistics')
      } finally {
        setIsLoadingDbStats(false)
      }
    }

    fetchDatabaseStats()
  }, [])

  // Helper function to format numbers with thousands separators
  const formatNumber = (num: number): string => {
    return num.toLocaleString('en-US')
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="text-white/60 mt-1">Configure categories and learning preferences</p>
      </div>

      {/* Confidence Mode Switcher */}
      <ConfidenceModeSwitcher />

      {/* Rollback History Panel */}
      <RollbackPanel />

      {/* Taxonomy / Category Management V3 */}
      <TaxonomySettings />

      {/* World Model / Identity Registry (Phase V4) */}
      <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass animate-fade-in" style={{ animationDelay: '50ms' }}>
        <IdentityManager />
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
        ) : learningStats && (learningStats.total_learning_events || 0) > 0 ? (
          <>
            {/* Main Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-white/5 rounded-lg p-4 animate-fade-in">
                <div className="flex items-center gap-2 mb-2">
                  <Target size={16} className="text-success" />
                  <div className="text-sm text-white/60">Total Learning Events</div>
                </div>
                <div className="text-3xl font-bold text-white">{formatNumber(learningStats.total_learning_events || 0)}</div>
                <div className="text-xs text-white/40 mt-1">AI classifications tracked</div>
              </div>

              <div className="bg-white/5 rounded-lg p-4 animate-fade-in" style={{ animationDelay: '100ms' }}>
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp size={16} className="text-primary" />
                  <div className="text-sm text-white/60">Unique Categories</div>
                </div>
                <div className="text-3xl font-bold text-white">{formatNumber(learningStats.unique_categories_learned || 0)}</div>
                <div className="text-xs text-white/40 mt-1">Patterns discovered</div>
              </div>

              <div className="bg-white/5 rounded-lg p-4 animate-fade-in" style={{ animationDelay: '200ms' }}>
                <div className="flex items-center gap-2 mb-2">
                  <Award size={16} className="text-warning" />
                  <div className="text-sm text-white/60">Top Confidence</div>
                </div>
                <div className="text-3xl font-bold text-white">{((learningStats.top_confidence_average || 0) * 100).toFixed(0)}%</div>
                <div className="text-xs text-white/40 mt-1">Average of top 10 events</div>
                {/* Progress bar */}
                <div className="mt-2 h-1.5 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-warning to-success transition-all duration-1000 ease-out"
                    style={{ width: `${(learningStats.top_confidence_average || 0) * 100}%` }}
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
                    <div className="text-lg font-bold text-white">{formatNumber(learningStats.image_events || 0)}</div>
                  </div>
                </div>

                <div className="bg-white/5 rounded-lg p-3 flex items-center gap-3">
                  <div className="p-2 bg-purple-500/20 rounded-lg">
                    <Video size={16} className="text-purple-400" />
                  </div>
                  <div>
                    <div className="text-xs text-white/60">Videos</div>
                    <div className="text-lg font-bold text-white">{formatNumber(learningStats.video_events || 0)}</div>
                  </div>
                </div>

                <div className="bg-white/5 rounded-lg p-3 flex items-center gap-3">
                  <div className="p-2 bg-pink-500/20 rounded-lg">
                    <Music size={16} className="text-pink-400" />
                  </div>
                  <div>
                    <div className="text-xs text-white/60">Audio</div>
                    <div className="text-lg font-bold text-white">{formatNumber(learningStats.audio_events || 0)}</div>
                  </div>
                </div>

                <div className="bg-white/5 rounded-lg p-3 flex items-center gap-3">
                  <div className="p-2 bg-green-500/20 rounded-lg">
                    <FileText size={16} className="text-green-400" />
                  </div>
                  <div>
                    <div className="text-xs text-white/60">Documents</div>
                    <div className="text-lg font-bold text-white">{formatNumber(learningStats.document_events || 0)}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Most Common Category */}
            {learningStats.most_common_category && (
              <div className="mt-4 p-3 bg-primary/10 border border-primary/20 rounded-lg">
                <div className="text-sm text-primary">
                  <strong>Most Common Category:</strong> {learningStats.most_common_category}
                  {learningStats.most_common_category && learningStats.category_distribution && learningStats.category_distribution[learningStats.most_common_category] &&
                    ` (${formatNumber(learningStats.category_distribution[learningStats.most_common_category] || 0)} files)`
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

      {/* Database Statistics */}
      <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass animate-fade-in">
        <div className="flex items-center gap-2 mb-4">
          <Database size={20} className="text-cyan-400" />
          <h2 className="text-xl font-semibold text-white">Database Statistics</h2>
        </div>

        {isLoadingDbStats ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400"></div>
          </div>
        ) : databaseStats ? (
          <>
            {/* Main Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-white/5 rounded-lg p-4 animate-fade-in">
                <div className="flex items-center gap-2 mb-2">
                  <Activity size={16} className="text-cyan-400" />
                  <div className="text-sm text-white/60">Total Operations</div>
                </div>
                <div className="text-3xl font-bold text-white">{formatNumber(databaseStats.total_operations)}</div>
                <div className="text-xs text-white/40 mt-1">File movements tracked</div>
              </div>

              <div className="bg-white/5 rounded-lg p-4 animate-fade-in" style={{ animationDelay: '100ms' }}>
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp size={16} className="text-success" />
                  <div className="text-sm text-white/60">Recent Activity</div>
                </div>
                <div className="text-3xl font-bold text-white">{formatNumber(databaseStats.recent_operations)}</div>
                <div className="text-xs text-white/40 mt-1">Last 7 days</div>
              </div>

              <div className="bg-white/5 rounded-lg p-4 animate-fade-in" style={{ animationDelay: '200ms' }}>
                <div className="flex items-center gap-2 mb-2">
                  <HardDrive size={16} className="text-purple-400" />
                  <div className="text-sm text-white/60">Storage Used</div>
                </div>
                <div className="text-3xl font-bold text-white">{databaseStats.total_db_size_mb} MB</div>
                <div className="text-xs text-white/40 mt-1">Total database size</div>
              </div>
            </div>

            {/* Database Breakdown */}
            <div className="mb-6">
              <div className="text-sm font-medium text-white/80 mb-3">Database Breakdown</div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="bg-white/5 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-xs text-white/60">Rollback DB</div>
                    <div className="text-xs font-mono text-cyan-400">{databaseStats.rollback_db_size_mb} MB</div>
                  </div>
                  <div className="text-sm font-bold text-white">{formatNumber(databaseStats.total_operations)} records</div>
                </div>

                <div className="bg-white/5 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-xs text-white/60">Learning DB</div>
                    <div className="text-xs font-mono text-cyan-400">{databaseStats.learning_db_size_mb} MB</div>
                  </div>
                  <div className="text-sm font-bold text-white">{formatNumber(databaseStats.total_learning_events_db)} records</div>
                </div>

                <div className="bg-white/5 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-xs text-white/60">Vector DB</div>
                    <div className="text-xs font-mono text-cyan-400">{databaseStats.vector_db_size_mb} MB</div>
                  </div>
                  <div className="text-sm font-bold text-white">Semantic search</div>
                </div>
              </div>
            </div>

            {/* Activity Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="bg-white/5 rounded-lg p-3">
                <div className="text-xs text-white/60 mb-1">Today's Operations</div>
                <div className="text-2xl font-bold text-white">{formatNumber(databaseStats.today_operations)}</div>
              </div>

              <div className="bg-white/5 rounded-lg p-3">
                <div className="text-xs text-white/60 mb-1">Avg Operations/Day</div>
                <div className="text-2xl font-bold text-white">{databaseStats.avg_operations_per_day}</div>
              </div>

              <div className="bg-white/5 rounded-lg p-3">
                <div className="text-xs text-white/60 mb-1">Avg Learning/Day</div>
                <div className="text-2xl font-bold text-white">{databaseStats.avg_learning_per_day}</div>
              </div>
            </div>

            <div className="mt-4 p-3 bg-cyan-500/10 border border-cyan-500/20 rounded-lg">
              <div className="text-sm text-cyan-400">
                <strong>Performance:</strong> All databases are optimized for fast lookups. Rollback history enables complete operation safety.
              </div>
            </div>
          </>
        ) : (
          <div className="py-12 text-center">
            <Database size={48} className="mx-auto text-white/20 mb-4" />
            <div className="text-white/60 text-lg font-medium mb-2">No database statistics available</div>
            <div className="text-white/40 text-sm max-w-md mx-auto">
              Database statistics will appear once the system starts processing files.
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
