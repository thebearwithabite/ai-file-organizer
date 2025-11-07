import { useState, useEffect } from 'react'
import { Sliders, Info } from 'lucide-react'
import { toast } from 'sonner'
import type { ConfidenceMode } from '../../types/api'
import { api } from '../../services/api'

interface ModeConfig {
  value: ConfidenceMode
  label: string
  color: string
  bgColor: string
  borderColor: string
  icon: string
  description: string
  helpText: string
}

const MODES: ModeConfig[] = [
  {
    value: 'never',
    label: 'Never Ask',
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/20',
    borderColor: 'border-blue-500/30',
    icon: '🔵',
    description: 'Fully automatic - no questions asked',
    helpText: 'Best for bulk processing. System will organize all files automatically without interruption.'
  },
  {
    value: 'minimal',
    label: 'Minimal Questions',
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    borderColor: 'border-green-500/30',
    icon: '🟢',
    description: 'Only ask about very uncertain files (40% threshold)',
    helpText: 'Quick processing with occasional questions. Good for when you trust the AI but want safety on edge cases.'
  },
  {
    value: 'smart',
    label: 'Smart Mode',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/20',
    borderColor: 'border-yellow-500/30',
    icon: '🟡',
    description: 'Balanced operation - ask when genuinely uncertain (70% threshold)',
    helpText: 'ADHD-friendly default. Asks questions when needed but not overwhelming. Recommended for most users.'
  },
  {
    value: 'always',
    label: 'Always Ask',
    color: 'text-red-400',
    bgColor: 'bg-red-500/20',
    borderColor: 'border-red-500/30',
    icon: '🔴',
    description: 'Human review for every file (100% threshold)',
    helpText: 'Maximum accuracy and control. Every file gets your approval before organization.'
  }
]

export default function ConfidenceModeSwitcher() {
  const [currentMode, setCurrentMode] = useState<ConfidenceMode>('smart')
  const [isLoading, setIsLoading] = useState(true)
  const [isUpdating, setIsUpdating] = useState(false)
  const [showTooltip, setShowTooltip] = useState<ConfidenceMode | null>(null)

  // Fetch current mode on mount
  useEffect(() => {
    const fetchMode = async () => {
      try {
        setIsLoading(true)
        const response = await api.getConfidenceMode()
        setCurrentMode(response.mode)
      } catch (error) {
        console.error('Error fetching confidence mode:', error)
        toast.error('Failed to load confidence mode')
      } finally {
        setIsLoading(false)
      }
    }

    fetchMode()
  }, [])

  const handleModeChange = async (newMode: ConfidenceMode) => {
    if (newMode === currentMode || isUpdating) return

    try {
      setIsUpdating(true)
      const response = await api.setConfidenceMode(newMode)
      setCurrentMode(response.mode)

      const modeConfig = MODES.find(m => m.value === newMode)
      toast.success(`Confidence mode updated to ${modeConfig?.label}`, {
        description: modeConfig?.description,
        duration: 3000,
      })
    } catch (error) {
      console.error('Error updating confidence mode:', error)
      toast.error('Failed to update confidence mode')
    } finally {
      setIsUpdating(false)
    }
  }

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
        <Sliders size={20} className="text-primary" />
        <h2 className="text-xl font-semibold text-white">Confidence Mode</h2>
        <div className="group relative ml-auto">
          <Info size={16} className="text-white/40 hover:text-white/60 cursor-help transition-colors" />
          <div className="invisible group-hover:visible absolute right-0 top-6 w-72 p-3 bg-black/90 backdrop-blur-xl border border-white/20 rounded-lg text-xs text-white/80 z-10 shadow-xl">
            Controls how often the AI asks for your input during file organization. ADHD-friendly modes help reduce decision fatigue while maintaining accuracy.
          </div>
        </div>
      </div>

      <p className="text-white/60 text-sm mb-6">
        Choose how often the AI should ask for your confirmation during file organization
      </p>

      {/* Mode Selection Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
        {MODES.map((mode) => {
          const isActive = currentMode === mode.value
          const isHovered = showTooltip === mode.value

          return (
            <button
              key={mode.value}
              onClick={() => handleModeChange(mode.value)}
              onMouseEnter={() => setShowTooltip(mode.value)}
              onMouseLeave={() => setShowTooltip(null)}
              disabled={isUpdating}
              className={`relative p-4 rounded-xl border-2 transition-all duration-200 text-left ${
                isActive
                  ? `${mode.bgColor} ${mode.borderColor} shadow-lg`
                  : 'bg-white/5 border-white/10 hover:bg-white/10 hover:border-white/20'
              } ${isUpdating ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <div className="flex items-start gap-3">
                <span className="text-2xl" aria-hidden="true">{mode.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className={`text-sm font-semibold mb-1 ${isActive ? mode.color : 'text-white'}`}>
                    {mode.label}
                  </div>
                  <div className="text-xs text-white/60 line-clamp-2">
                    {mode.description}
                  </div>
                </div>
                {isActive && (
                  <div className="flex-shrink-0">
                    <div className={`w-2 h-2 rounded-full ${mode.color.replace('text-', 'bg-')} animate-pulse`} />
                  </div>
                )}
              </div>

              {/* Tooltip on hover */}
              {isHovered && !isActive && (
                <div className="absolute left-0 right-0 top-full mt-2 p-3 bg-black/90 backdrop-blur-xl border border-white/20 rounded-lg text-xs text-white/80 z-10 shadow-xl">
                  {mode.helpText}
                </div>
              )}
            </button>
          )
        })}
      </div>

      {/* Current Mode Info */}
      <div className={`p-4 rounded-lg border-2 ${
        MODES.find(m => m.value === currentMode)?.bgColor
      } ${
        MODES.find(m => m.value === currentMode)?.borderColor
      }`}>
        <div className="flex items-start gap-3">
          <span className="text-xl" aria-hidden="true">
            {MODES.find(m => m.value === currentMode)?.icon}
          </span>
          <div className="flex-1">
            <div className="text-sm font-semibold text-white mb-1">
              Current Mode: {MODES.find(m => m.value === currentMode)?.label}
            </div>
            <div className="text-xs text-white/70">
              {MODES.find(m => m.value === currentMode)?.helpText}
            </div>
          </div>
        </div>
      </div>

      {/* ADHD-Friendly Note */}
      <div className="mt-4 p-3 bg-primary/10 border border-primary/20 rounded-lg">
        <div className="text-xs text-primary">
          <strong>ADHD-Friendly Design:</strong> Smart Mode (🟡) is recommended as the default. It reduces decision fatigue by only asking when the AI is genuinely uncertain, helping you stay focused without overwhelming you with questions.
        </div>
      </div>
    </div>
  )
}
