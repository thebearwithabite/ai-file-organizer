import { useState, useEffect } from 'react'
import {
    User,
    Dog,
    MapPin,
    Plus,
    Edit2,
    Trash2,
    Activity,
    Fingerprint,
    ShieldAlert,
    Search,
    X
} from 'lucide-react'
import { identityService } from '../../services/identities'
import type { Identity } from '../../services/identities'
import { toast } from 'sonner'

const ENTITY_TYPES = [
    { value: 'person', label: 'Person', icon: <User size={16} /> },
    { value: 'pet', label: 'Pet', icon: <Dog size={16} /> },
    { value: 'location', label: 'Location', icon: <MapPin size={16} /> },
    { value: 'object', label: 'Object', icon: <Activity size={16} /> }
]

export default function IdentityManager() {
    const [identities, setIdentities] = useState<Identity[]>([])
    const [loading, setLoading] = useState(true)
    const [searchTerm, setSearchTerm] = useState('')
    const [isDialogOpen, setIsDialogOpen] = useState(false)
    const [editingId, setEditingId] = useState<string | null>(null)

    // Form State
    const [formData, setFormData] = useState<Partial<Identity>>({
        id: '',
        name: '',
        type: 'person',
        description: '',
        priority: 1
    })

    const fetchIdentities = async () => {
        try {
            setLoading(true)
            const data = await identityService.getIdentities()
            setIdentities(data)
        } catch (err) {
            console.error(err)
            toast.error('Failed to load "World Model" registry')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchIdentities()
    }, [])

    const handleOpenDialog = (identity?: Identity) => {
        if (identity) {
            setEditingId(identity.id)
            setFormData(identity)
        } else {
            setEditingId(null)
            setFormData({
                id: '',
                name: '',
                type: 'person',
                description: '',
                priority: 1
            })
        }
        setIsDialogOpen(true)
    }

    const handleSave = async () => {
        if (!formData.id || !formData.name) {
            toast.error('ID and Name are required')
            return
        }

        try {
            if (editingId) {
                await identityService.updateIdentity(editingId, formData)
                toast.success(`Updated ${formData.name}`)
            } else {
                await identityService.createIdentity(formData as Identity)
                toast.success(`Registered ${formData.name}`)
            }
            setIsDialogOpen(false)
            fetchIdentities()
        } catch (err) {
            toast.error('Failed to save identity')
        }
    }

    const handleDelete = async (id: string) => {
        if (!confirm('Are you sure you want to remove this entity from the World Model?')) return

        try {
            await identityService.deleteIdentity(id)
            toast.success('Identity removed')
            fetchIdentities()
        } catch (err) {
            toast.error('Failed to delete identity')
        }
    }

    const getIconForType = (type: string) => {
        switch (type) {
            case 'person': return <User size={18} />
            case 'pet': return <Dog size={18} />
            case 'location': return <MapPin size={18} />
            default: return <Fingerprint size={18} />
        }
    }

    const filteredIdentities = identities.filter(id =>
        id.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        id.id.toLowerCase().includes(searchTerm.toLowerCase())
    )

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <div className="flex items-center gap-2">
                        <Activity size={24} className="text-purple-400 font-bold" />
                        <h2 className="text-xl font-bold text-white">World Model Registry</h2>
                        <span className="px-2 py-0.5 bg-gradient-to-r from-purple-600 to-pink-600 text-white text-[10px] font-bold rounded-full uppercase tracking-wider">
                            Phase V4
                        </span>
                    </div>
                    <p className="text-white/60 text-sm mt-1">
                        Teach the system to recognize specific people, pets, and creative locations.
                    </p>
                </div>
                <button
                    onClick={() => handleOpenDialog()}
                    className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-medium rounded-xl transition-all shadow-lg hover:shadow-indigo-500/20 active:scale-95"
                >
                    <Plus size={18} />
                    Register Entity
                </button>
            </div>

            {/* Search Bar */}
            <div className="relative">
                <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" />
                <input
                    type="text"
                    placeholder="Search entities by name or system ID..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-purple-500/50 transition-all"
                />
            </div>

            {loading ? (
                <div className="flex justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
                </div>
            ) : filteredIdentities.length === 0 ? (
                <div className="py-12 text-center bg-white/5 border border-white/10 border-dashed rounded-2xl">
                    <Fingerprint size={48} className="mx-auto text-white/10 mb-2" />
                    <p className="text-white/40">No entities found in the World Model.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredIdentities.map((identity) => (
                        <div key={identity.id} className="group bg-white/5 hover:bg-white/[0.08] border border-white/10 hover:border-purple-500/50 rounded-2xl p-5 transition-all shadow-sm hover:shadow-purple-500/10 relative overflow-hidden">
                            <div className="flex justify-between items-start mb-4">
                                <div className="flex gap-3">
                                    <div className="p-2.5 bg-purple-500/20 text-purple-400 rounded-xl">
                                        {getIconForType(identity.type)}
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-semibold text-white group-hover:text-purple-300 transition-colors line-clamp-1">
                                            {identity.name}
                                        </h3>
                                        <div className="flex items-center gap-1 text-[10px] text-white/40 font-mono">
                                            <Fingerprint size={10} />
                                            {identity.id}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex gap-1">
                                    <button
                                        onClick={() => handleOpenDialog(identity)}
                                        className="p-1.5 text-white/40 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                                    >
                                        <Edit2 size={14} />
                                    </button>
                                    <button
                                        onClick={() => handleDelete(identity.id)}
                                        className="p-1.5 text-white/40 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            </div>

                            <p className="text-sm text-white/70 line-clamp-3 mb-4 h-15 leading-relaxed">
                                {identity.description || 'No description provided.'}
                            </p>

                            <div className="flex items-center gap-2">
                                <span className="text-[10px] px-2 py-0.5 bg-white/10 text-white/60 rounded-full capitalize border border-white/5 font-medium">
                                    {identity.type}
                                </span>
                                {identity.priority >= 10 && (
                                    <span className="text-[10px] px-2 py-0.5 bg-amber-500/20 text-amber-400 rounded-full border border-amber-500/20 font-bold">
                                        Priority Label
                                    </span>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Calibration Note */}
            <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-2xl flex gap-3 items-start animate-fade-in">
                <ShieldAlert size={20} className="text-indigo-400 shrink-0 mt-0.5" />
                <div className="text-xs text-white/60 leading-relaxed">
                    <strong className="text-indigo-300">Identity Context Enforced:</strong> These entities are automatically injected into Vision prompts. Descriptions are used as "Visual Cues".
                    <span className="block mt-1">Example: "Usually wears blue hat" or "Small black dog with white paws". This helps the AI differentiate between unknown subjects and known entities.</span>
                </div>
            </div>

            {/* Custom Dialog (Glassmorphic) */}
            {isDialogOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in">
                    <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setIsDialogOpen(false)} />
                    <div className="relative w-full max-w-lg bg-[#111] border border-white/10 rounded-3xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
                        <div className="p-6 border-b border-white/10 flex justify-between items-center">
                            <h2 className="text-xl font-bold text-white">
                                {editingId ? 'Edit Entity' : 'Register New Entity'}
                            </h2>
                            <button
                                onClick={() => setIsDialogOpen(false)}
                                className="p-2 text-white/40 hover:text-white transition-colors"
                            >
                                <X size={20} />
                            </button>
                        </div>

                        <div className="p-6 space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1.5">
                                    <label className="text-xs font-medium text-white/60 ml-1">System ID</label>
                                    <input
                                        type="text"
                                        disabled={!!editingId}
                                        value={formData.id}
                                        onChange={(e) => setFormData({ ...formData, id: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '') })}
                                        placeholder="e.g. ryan_human"
                                        className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50 disabled:opacity-50"
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-xs font-medium text-white/60 ml-1">Display Name</label>
                                    <input
                                        type="text"
                                        value={formData.name}
                                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                        placeholder="e.g. Ryan"
                                        className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                                    />
                                </div>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-xs font-medium text-white/60 ml-1">Entity Type</label>
                                <select
                                    value={formData.type}
                                    onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                                    className="w-full px-4 py-2 bg-[#1a1a1a] border border-white/10 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                                >
                                    {ENTITY_TYPES.map(opt => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-xs font-medium text-white/60 ml-1">Visual Cues & Context</label>
                                <textarea
                                    rows={4}
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    placeholder="Describe distinctive physical features or recurring contexts..."
                                    className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50 resize-none"
                                />
                                <p className="text-[10px] text-white/40 ml-1">
                                    Gemini uses this to ground visual identification in your specific "World".
                                </p>
                            </div>
                        </div>

                        <div className="p-6 bg-white/5 border-t border-white/10 flex justify-end gap-3">
                            <button
                                onClick={() => setIsDialogOpen(false)}
                                className="px-6 py-2 bg-white/5 hover:bg-white/10 text-white font-medium rounded-xl transition-all"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSave}
                                className="px-6 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold rounded-xl transition-all shadow-lg shadow-indigo-600/20 active:scale-95"
                            >
                                {editingId ? 'Update Identity' : 'Save Entity'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
