import { useNavigate } from 'react-router-dom'
import { Upload, Search, RotateCcw, Zap } from 'lucide-react'
import { motion } from 'framer-motion'
import { api } from '../../services/api'
import { toast } from 'sonner'

export default function QuickActionPanel() {
  const navigate = useNavigate()

  const handleRunOrchestration = async () => {
    try {
      await api.triggerOrchestration()
      toast.success('Orchestration triggered', {
        description: 'The system is now organizing files in the background.'
      })
    } catch (error) {
      console.error('Failed to trigger orchestration:', error)
      toast.error('Failed to trigger orchestration')
    }
  }

  const actions = [
    {
      icon: Upload,
      label: 'Upload Files',
      description: 'Organize new files',
      onClick: () => navigate('/organize'),
      color: 'bg-primary hover:bg-primary-hover',
    },
    {
      icon: Search,
      label: 'Search',
      description: 'Find anything',
      onClick: () => navigate('/search'),
      color: 'bg-accent-purple hover:bg-accent-purple-hover',
    },
    {
      icon: RotateCcw,
      label: 'Rollback',
      description: 'Undo operations',
      onClick: () => navigate('/rollback'),
      color: 'bg-warning hover:bg-warning/90 text-black',
    },
    {
      icon: Zap,
      label: 'Run Orchestration',
      description: 'Manual organization run',
      onClick: handleRunOrchestration,
      color: 'bg-success hover:bg-success/90',
    },
  ]

  return (
    <div className="bg-white/[0.07] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-glass">
      <h2 className="text-xl font-semibold text-white mb-4">Quick Actions</h2>

      <div className="space-y-3">
        {actions.map((action) => {
          const Icon = action.icon
          return (
            <motion.button
              key={action.label}
              onClick={action.onClick}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={`w-full flex items-center gap-4 p-4 rounded-xl ${action.color} transition-colors text-white`}
            >
              <Icon size={24} />
              <div className="flex-1 text-left">
                <div className="font-semibold">{action.label}</div>
                <div className="text-sm opacity-80">{action.description}</div>
              </div>
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}
