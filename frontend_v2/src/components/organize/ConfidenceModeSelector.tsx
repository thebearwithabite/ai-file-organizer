import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api } from '../../services/api'
import { cn } from '../../lib/utils'

const modes = [
  {
    value: 'never',
    emoji: '🔴',
    label: 'NEVER',
    description: 'Fully automatic, no questions',
    threshold: 0,
  },
  {
    value: 'minimal',
    emoji: '🟡',
    label: 'MINIMAL',
    description: 'Only very uncertain files',
    threshold: 40,
  },
  {
    value: 'smart',
    emoji: '🟢',
    label: 'SMART',
    description: 'Balanced (recommended for ADHD)',
    threshold: 70,
    recommended: true,
  },
  {
    value: 'always',
    emoji: '🔵',
    label: 'ALWAYS',
    description: 'Review every single file',
    threshold: 100,
  },
]

export default function ConfidenceModeSelector() {
  const [selectedMode, setSelectedMode] = useState('smart')

  const { mutate: updateMode } = useMutation({
    mutationFn: api.updateConfidenceMode,
    onSuccess: () => {
      toast.success('Confidence mode updated')
    },
  })

  const handleModeChange = (mode: string) => {
    setSelectedMode(mode)
    updateMode(mode)
  }

  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-4">Confidence Mode</h3>
      <p className="text-sm text-white/60 mb-4">
        Controls how often the AI asks for your input when organizing files
      </p>

      <div className="space-y-3">
        {modes.map((mode) => (
          <button
            key={mode.value}
            onClick={() => handleModeChange(mode.value)}
            className={cn(
              "w-full text-left p-4 rounded-xl border-2 transition-all",
              selectedMode === mode.value
                ? "border-primary bg-primary/10"
                : "border-white/10 bg-white/[0.05] hover:border-white/20"
            )}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="text-2xl">{mode.emoji}</div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white">{mode.label}</span>
                    {mode.recommended && (
                      <span className="text-xs px-2 py-0.5 bg-success/20 text-success rounded">
                        Recommended
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-white/60">{mode.description}</div>
                </div>
              </div>
              <div className="text-2xl font-bold text-white/40">{mode.threshold}%</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
