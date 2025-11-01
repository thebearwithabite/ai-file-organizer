import { useQuery } from '@tanstack/react-query'
import { FolderOpen, Brain, Settings, Search } from 'lucide-react'
import { api } from '../../services/api'
import type { LearningStats } from '../../types/api'

export default function MetricsGrid() {
  const { data } = useQuery<LearningStats>({
    queryKey: ['learning-stats'],
    queryFn: api.getLearningStats,
  })

  const metrics = [
    {
      icon: FolderOpen,
      label: 'Files Organized Today',
      value: data?.files_organized_today ?? 12,
      color: 'text-blue-400',
    },
    {
      icon: Brain,
      label: 'Patterns Learned',
      value: data?.patterns_count ?? 247,
      color: 'text-purple-400',
    },
    {
      icon: Settings,
      label: 'Confidence Mode',
      value: data?.confidence_mode ?? 'SMART',
      color: 'text-green-400',
    },
    {
      icon: Search,
      label: 'Searches Today',
      value: data?.searches_today ?? 8,
      color: 'text-yellow-400',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {metrics.map((metric) => {
        const Icon = metric.icon
        return (
          <div
            key={metric.label}
            className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass"
          >
            <div className="flex items-center gap-3 mb-2">
              <Icon size={20} className={metric.color} />
              <div className="text-xs text-white/60">{metric.label}</div>
            </div>
            <div className="text-3xl font-bold text-white">{metric.value}</div>
          </div>
        )
      })}
    </div>
  )
}
