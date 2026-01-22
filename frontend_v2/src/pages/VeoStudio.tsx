import { useState } from 'react'
import { api } from '../services/api'
import type { VEOScriptAnalysis, VEOShotList, VEOAsset, VEOShot } from '../types/api'
import { Upload, FileText, Film, Image, Wand2, Download, List } from 'lucide-react'

type TabType = 'script' | 'assets' | 'shots' | 'shotbook'

export default function VeoStudio() {
  const [activeTab, setActiveTab] = useState<TabType>('script')
  const [scriptContent, setScriptContent] = useState('')
  const [projectName, setProjectName] = useState('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [isGeneratingShotList, setIsGeneratingShotList] = useState(false)
  const [analysis, setAnalysis] = useState<VEOScriptAnalysis | null>(null)
  const [shotList, setShotList] = useState<VEOShotList | null>(null)
  const [selectedShot, setSelectedShot] = useState<VEOShot | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleScriptUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      const text = await file.text()
      setScriptContent(text)
      setError(null)
    } catch (err) {
      setError('Failed to read file')
      console.error('File read error:', err)
    }
  }

  const handleAnalyzeScript = async () => {
    if (!scriptContent.trim()) {
      setError('Please enter or upload a script first')
      return
    }

    setIsAnalyzing(true)
    setError(null)

    try {
      const result = await api.analyzeScript(scriptContent, projectName || undefined)
      
      if (result.success) {
        setAnalysis(result)
        setActiveTab('assets')
      } else {
        setError(result.error || 'Analysis failed')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed')
      console.error('Analysis error:', err)
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleGenerateShotList = async () => {
    if (!scriptContent.trim()) {
      setError('Please enter or upload a script first')
      return
    }

    setIsGeneratingShotList(true)
    setError(null)

    try {
      const result = await api.generateShotList(
        scriptContent,
        projectName || undefined,
        analysis?.assets
      )
      
      if (result.success) {
        setShotList(result)
        setActiveTab('shots')
      } else {
        setError(result.error || 'Shot list generation failed')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Shot list generation failed')
      console.error('Shot list error:', err)
    } finally {
      setIsGeneratingShotList(false)
    }
  }

  const handleGenerateKeyframe = async (shotId: string, description: string) => {
    try {
      const result = await api.generateKeyframe(shotId, description, false)
      
      if (!result.success) {
        console.log('Keyframe generation:', result.error)
      }
    } catch (err) {
      console.error('Keyframe generation error:', err)
    }
  }

  const exportToJSON = () => {
    const exportData = {
      project_name: projectName,
      script: scriptContent,
      analysis: analysis,
      shots: shotList?.shots || []
    }

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${projectName || 'veo_project'}_${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const renderTabButton = (tab: TabType, icon: React.ReactNode, label: string) => (
    <button
      onClick={() => setActiveTab(tab)}
      className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all ${
        activeTab === tab
          ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
          : 'text-white/60 hover:text-white/90 hover:bg-white/5'
      }`}
    >
      {icon}
      <span>{label}</span>
    </button>
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">VEO Studio</h1>
          <p className="text-white/60">Transform scripts into VEO 3.1 prompts with AI-powered analysis</p>
        </div>
        <button
          onClick={exportToJSON}
          disabled={!analysis && !shotList}
          className="flex items-center gap-2 px-4 py-2 bg-green-500/20 text-green-400 border border-green-500/30 rounded-lg hover:bg-green-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          <Download className="w-4 h-4" />
          Export Project
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-white/10 pb-2">
        {renderTabButton('script', <FileText className="w-5 h-5" />, 'Script')}
        {renderTabButton('assets', <Image className="w-5 h-5" />, `Assets ${analysis ? `(${analysis.assets.length})` : ''}`)}
        {renderTabButton('shots', <Film className="w-5 h-5" />, `Shots ${shotList ? `(${shotList.total_shots})` : ''}`)}
        {renderTabButton('shotbook', <List className="w-5 h-5" />, 'Shot Book')}
      </div>

      {/* Tab Content */}
      <div className="min-h-[600px]">
        {/* Script Tab */}
        {activeTab === 'script' && (
          <div className="space-y-4">
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-lg p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-white/80 mb-2">
                  Project Name (Optional)
                </label>
                <input
                  type="text"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="My VEO Project"
                  className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:border-blue-500/50"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/80 mb-2">
                  Script Content
                </label>
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <label className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-blue-500/20 border border-blue-500/30 rounded-lg text-blue-400 hover:bg-blue-500/30 cursor-pointer transition-all">
                      <Upload className="w-5 h-5" />
                      Upload Script File
                      <input
                        type="file"
                        accept=".txt,.fountain,.pdf"
                        onChange={handleScriptUpload}
                        className="hidden"
                      />
                    </label>
                  </div>
                  
                  <textarea
                    value={scriptContent}
                    onChange={(e) => setScriptContent(e.target.value)}
                    placeholder="Paste your script here or upload a file...

Example:
INT. OFFICE - DAY

JOHN
(excited)
We need to finish this project!

SARAH enters from stage left.

SARAH
I have the solution!"
                    className="w-full h-96 px-4 py-3 bg-black/30 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-blue-500/50 font-mono text-sm resize-none"
                  />
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={handleAnalyzeScript}
                  disabled={isAnalyzing || !scriptContent.trim()}
                  className="flex items-center gap-2 px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium"
                >
                  <Wand2 className={`w-5 h-5 ${isAnalyzing ? 'animate-spin' : ''}`} />
                  {isAnalyzing ? 'Analyzing...' : 'Analyze Script'}
                </button>

                <button
                  onClick={handleGenerateShotList}
                  disabled={isGeneratingShotList || !scriptContent.trim()}
                  className="flex items-center gap-2 px-6 py-3 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium"
                >
                  <Film className={`w-5 h-5 ${isGeneratingShotList ? 'animate-spin' : ''}`} />
                  {isGeneratingShotList ? 'Generating...' : 'Generate Shot List'}
                </button>
              </div>

              {analysis && (
                <div className="mt-4 p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <div className="text-2xl font-bold text-green-400">{analysis.scene_count}</div>
                      <div className="text-sm text-white/60">Scenes</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-green-400">{analysis.shot_count}</div>
                      <div className="text-sm text-white/60">Est. Shots</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-green-400">{analysis.assets.length}</div>
                      <div className="text-sm text-white/60">Assets</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Assets Tab */}
        {activeTab === 'assets' && (
          <div className="space-y-4">
            {analysis ? (
              <>
                <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-lg p-6">
                  <h2 className="text-xl font-bold text-white mb-4">Detected Assets</h2>
                  
                  {/* Group by type */}
                  {['character', 'location', 'prop'].map((type) => {
                    const assetsOfType = analysis.assets.filter((a) => a.type === type)
                    if (assetsOfType.length === 0) return null

                    return (
                      <div key={type} className="mb-6">
                        <h3 className="text-lg font-semibold text-white/80 mb-3 capitalize flex items-center gap-2">
                          {type === 'character' && '👤'}
                          {type === 'location' && '📍'}
                          {type === 'prop' && '🎬'}
                          {type}s ({assetsOfType.length})
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                          {assetsOfType.map((asset, idx) => (
                            <div
                              key={idx}
                              className="p-4 bg-white/5 border border-white/10 rounded-lg hover:border-white/20 transition-all"
                            >
                              <div className="flex items-start justify-between mb-2">
                                <div className="font-medium text-white">{asset.name}</div>
                                <div className="text-xs text-white/60 bg-white/10 px-2 py-1 rounded">
                                  {asset.occurrences}x
                                </div>
                              </div>
                              {asset.description && (
                                <div className="text-sm text-white/60">{asset.description}</div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </>
            ) : (
              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-lg p-12 text-center">
                <Image className="w-16 h-16 mx-auto mb-4 text-white/40" />
                <p className="text-white/60 mb-2">No assets analyzed yet</p>
                <p className="text-sm text-white/40">Analyze a script to detect characters, locations, and props</p>
              </div>
            )}
          </div>
        )}

        {/* Shots Tab */}
        {activeTab === 'shots' && (
          <div className="space-y-4">
            {shotList && shotList.shots.length > 0 ? (
              <>
                <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-lg p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-bold text-white">Shot List</h2>
                    <div className="text-sm text-white/60">
                      Total Duration: {shotList.total_duration_estimate?.toFixed(1)}s
                    </div>
                  </div>

                  <div className="space-y-2">
                    {shotList.shots.map((shot) => (
                      <div
                        key={shot.shot_id}
                        onClick={() => setSelectedShot(shot)}
                        className={`p-4 bg-white/5 border rounded-lg cursor-pointer transition-all ${
                          selectedShot?.shot_id === shot.shot_id
                            ? 'border-blue-500/50 bg-blue-500/10'
                            : 'border-white/10 hover:border-white/20'
                        }`}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-3">
                            <div className="text-2xl font-bold text-white/40">
                              {shot.shot_number}
                            </div>
                            <div>
                              <div className="font-medium text-white">{shot.shot_id}</div>
                              {shot.location && (
                                <div className="text-sm text-white/60">{shot.location}</div>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {shot.duration_estimate && (
                              <div className="text-xs text-white/60 bg-white/10 px-2 py-1 rounded">
                                {shot.duration_estimate}s
                              </div>
                            )}
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                handleGenerateKeyframe(shot.shot_id, shot.description)
                              }}
                              className="text-xs px-3 py-1 bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded hover:bg-purple-500/30 transition-all"
                            >
                              Generate Keyframe
                            </button>
                          </div>
                        </div>
                        <div className="text-sm text-white/80">{shot.description}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-lg p-12 text-center">
                <Film className="w-16 h-16 mx-auto mb-4 text-white/40" />
                <p className="text-white/60 mb-2">No shots generated yet</p>
                <p className="text-sm text-white/40">Generate a shot list from your script</p>
              </div>
            )}
          </div>
        )}

        {/* Shot Book Tab */}
        {activeTab === 'shotbook' && (
          <div className="space-y-4">
            {selectedShot ? (
              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-lg p-6">
                <h2 className="text-2xl font-bold text-white mb-6">
                  Shot {selectedShot.shot_number}: {selectedShot.shot_id}
                </h2>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Keyframe Placeholder */}
                  <div className="bg-black/30 border border-white/10 rounded-lg aspect-video flex items-center justify-center">
                    <div className="text-center">
                      <Image className="w-12 h-12 mx-auto mb-2 text-white/40" />
                      <p className="text-white/60 text-sm">Keyframe (Phase 2)</p>
                    </div>
                  </div>

                  {/* Shot Details */}
                  <div className="space-y-4">
                    <div>
                      <div className="text-sm font-medium text-white/60 mb-1">Description</div>
                      <div className="text-white">{selectedShot.description}</div>
                    </div>

                    {selectedShot.location && (
                      <div>
                        <div className="text-sm font-medium text-white/60 mb-1">Location</div>
                        <div className="text-white">{selectedShot.location}</div>
                      </div>
                    )}

                    {selectedShot.camera_angle && (
                      <div>
                        <div className="text-sm font-medium text-white/60 mb-1">Camera Angle</div>
                        <div className="text-white">{selectedShot.camera_angle}</div>
                      </div>
                    )}

                    {selectedShot.duration_estimate && (
                      <div>
                        <div className="text-sm font-medium text-white/60 mb-1">Duration</div>
                        <div className="text-white">{selectedShot.duration_estimate}s</div>
                      </div>
                    )}

                    {selectedShot.characters.length > 0 && (
                      <div>
                        <div className="text-sm font-medium text-white/60 mb-1">Characters</div>
                        <div className="flex flex-wrap gap-2">
                          {selectedShot.characters.map((char, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-1 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded text-sm"
                            >
                              {char}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {selectedShot.assets_needed.length > 0 && (
                      <div>
                        <div className="text-sm font-medium text-white/60 mb-1">Assets Needed</div>
                        <div className="flex flex-wrap gap-2">
                          {selectedShot.assets_needed.map((asset, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-1 bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded text-sm"
                            >
                              {asset}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* VEO JSON Preview */}
                <div className="mt-6">
                  <div className="text-sm font-medium text-white/60 mb-2">VEO 3.1 JSON Preview (Phase 2)</div>
                  <div className="bg-black/30 border border-white/10 rounded-lg p-4 font-mono text-xs text-white/60">
                    <pre>{JSON.stringify({ shot_id: selectedShot.shot_id, description: selectedShot.description }, null, 2)}</pre>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-lg p-12 text-center">
                <List className="w-16 h-16 mx-auto mb-4 text-white/40" />
                <p className="text-white/60 mb-2">No shot selected</p>
                <p className="text-sm text-white/40">Select a shot from the Shots tab to view details</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

