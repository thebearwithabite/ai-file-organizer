import React, { useState, useEffect } from 'react';
import {
    Edit,
    FolderEdit,
    Lock,
    Plus,
    AlertCircle,
    Info,
    Loader2,
    X,
    Save
} from 'lucide-react';
import { taxonomyService } from '../../services/taxonomy';
import type { Category, RenameResult } from '../../services/taxonomy';

export const TaxonomySettings: React.FC = () => {
    const [categories, setCategories] = useState<Record<string, Category>>({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Edit Metadata State
    const [editCategory, setEditCategory] = useState<Category | null>(null);
    const [editAliases, setEditAliases] = useState('');
    const [editKeywords, setEditKeywords] = useState('');

    // Rename State
    const [renameCategory, setRenameCategory] = useState<Category | null>(null);
    const [newName, setNewName] = useState('');
    const [renameResult, setRenameResult] = useState<RenameResult | null>(null);
    const [renaming, setRenaming] = useState(false);

    // Create State
    const [createDialogOpen, setCreateDialogOpen] = useState(false);
    const [newCategory, setNewCategory] = useState({
        id: '',
        display_name: '',
        folder_name: '',
        parent_path: '',
        aliases: '',
        keywords: ''
    });
    const [creating, setCreating] = useState(false);
    const [createError, setCreateError] = useState<string | null>(null);

    useEffect(() => {
        loadTaxonomy();
    }, []);

    const loadTaxonomy = async () => {
        try {
            setLoading(true);
            const data = await taxonomyService.getTaxonomy();
            setCategories(data);
            setError(null);
        } catch (err: any) {
            setError("Failed to load taxonomy");
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleEditOpen = (cat: Category) => {
        setEditCategory(cat);
        setEditAliases(cat.aliases?.join(', ') || '');
        setEditKeywords(cat.keywords?.join(', ') || '');
    };

    const handleEditSave = async () => {
        if (!editCategory) return;
        try {
            const aliases = editAliases.split(',').map(s => s.trim()).filter(s => s);
            const keywords = editKeywords.split(',').map(s => s.trim()).filter(s => s);

            await taxonomyService.updateCategory(editCategory.id, { aliases, keywords });
            await loadTaxonomy();
            setEditCategory(null);
        } catch (err) {
            console.error("Update failed", err);
        }
    };

    const handleRenameOpen = (cat: Category) => {
        if (cat.locked) return;
        setRenameCategory(cat);
        setNewName(cat.folder_name);
        setRenameResult(null);
    };

    const handleRenameSubmit = async () => {
        if (!renameCategory) return;
        setRenaming(true);
        setRenameResult(null);
        try {
            const result = await taxonomyService.renameCategory(renameCategory.id, newName);
            setRenameResult(result);
            if (result.status === 'success') {
                setTimeout(() => {
                    loadTaxonomy();
                    setRenameCategory(null);
                }, 1000);
            }
        } catch (err: any) {
            setRenameResult({ status: 'error', message: err.message });
        } finally {
            setRenaming(false);
        }
    };

    const handleCreateOpen = () => {
        setNewCategory({
            id: '',
            display_name: '',
            folder_name: '',
            parent_path: '',
            aliases: '',
            keywords: ''
        });
        setCreateError(null);
        setCreateDialogOpen(true);
    };

    const handleCreateSubmit = async () => {
        setCreating(true);
        setCreateError(null);
        try {
            const aliases = newCategory.aliases.split(',').map(s => s.trim()).filter(s => s);
            const keywords = newCategory.keywords.split(',').map(s => s.trim()).filter(s => s);

            await taxonomyService.createCategory({
                ...newCategory,
                aliases,
                keywords
            });
            await loadTaxonomy();
            setCreateDialogOpen(false);
        } catch (err: any) {
            setCreateError(err.message || "Failed to create category");
        } finally {
            setCreating(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center p-12">
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-xl text-destructive flex items-center gap-3">
                <AlertCircle size={20} />
                <span>{error}</span>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h2 className="text-xl font-bold text-white">Category Management (Taxonomy V3)</h2>
                    <p className="text-sm text-white/60">Configure AI classification logic and folder structures</p>
                </div>
                <button
                    onClick={handleCreateOpen}
                    className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-xl transition-colors font-medium"
                >
                    <Plus size={18} />
                    Add New Category
                </button>
            </div>

            <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl text-blue-200 flex items-start gap-3">
                <Info className="shrink-0 mt-0.5" size={20} />
                <p className="text-sm">
                    Changes here affect the AI's classification logic and the physical folder structure.
                    Renaming a category will rename its folder on disk.
                </p>
            </div>

            <div className="bg-white/[0.05] border border-white/10 rounded-2xl overflow-hidden shadow-glass">
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead>
                            <tr className="border-b border-white/10 bg-white/5">
                                <th className="px-6 py-4 text-xs font-semibold text-white/60 uppercase tracking-wider">Display Name</th>
                                <th className="px-6 py-4 text-xs font-semibold text-white/60 uppercase tracking-wider">Folder Path</th>
                                <th className="px-6 py-4 text-xs font-semibold text-white/60 uppercase tracking-wider">Keywords</th>
                                <th className="px-6 py-4 text-xs font-semibold text-white/60 uppercase tracking-wider whitespace-nowrap">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/10">
                            {Object.values(categories).map((cat) => (
                                <tr key={cat.id} className="hover:bg-white/[0.02] transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2">
                                            <span className="font-medium text-white">{cat.display_name}</span>
                                            {cat.locked && (
                                                <div title="Locked System Category">
                                                    <Lock size={14} className="text-white/40" />
                                                </div>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 font-mono text-sm text-white/70">
                                        <span className="px-2 py-0.5 bg-white/5 rounded border border-white/10">
                                            {cat.parent_path ? cat.parent_path + '/' : ''}{cat.folder_name}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 max-w-xs truncate text-sm text-white/60">
                                        {cat.keywords?.join(', ')}
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={() => handleEditOpen(cat)}
                                                disabled={cat.locked}
                                                className="p-2 hover:bg-white/10 rounded-lg text-white/60 hover:text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                                                title="Edit Metadata"
                                            >
                                                <Edit size={18} />
                                            </button>
                                            <button
                                                onClick={() => handleRenameOpen(cat)}
                                                disabled={cat.locked}
                                                className="p-2 hover:bg-white/10 rounded-lg text-white/60 hover:text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                                                title="Rename Category & Folder"
                                            >
                                                <FolderEdit size={18} />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Edit Dialog */}
            {editCategory && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
                    <div className="bg-[#1a1a1a] border border-white/20 rounded-2xl w-full max-w-md shadow-2xl animate-in fade-in zoom-in duration-200">
                        <div className="flex justify-between items-center p-6 border-b border-white/10">
                            <h3 className="text-lg font-bold text-white">Edit Metadata: {editCategory.display_name}</h3>
                            <button onClick={() => setEditCategory(null)} className="text-white/40 hover:text-white">
                                <X size={20} />
                            </button>
                        </div>
                        <div className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-white/60 mb-1.5 text-left">Aliases (comma separated)</label>
                                <input
                                    type="text"
                                    value={editAliases}
                                    onChange={(e) => setEditAliases(e.target.value)}
                                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
                                    placeholder="e.g. Snaps, Pics"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-white/60 mb-1.5 text-left">Keywords (comma separated)</label>
                                <input
                                    type="text"
                                    value={editKeywords}
                                    onChange={(e) => setEditKeywords(e.target.value)}
                                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
                                    placeholder="e.g. invoice, bill, payment"
                                />
                            </div>
                        </div>
                        <div className="flex justify-end gap-3 p-6 border-t border-white/10">
                            <button onClick={() => setEditCategory(null)} className="px-4 py-2 text-white/60 hover:text-white transition-colors">Cancel</button>
                            <button onClick={handleEditSave} className="flex items-center gap-2 px-6 py-2 bg-primary hover:bg-primary/90 text-white rounded-xl transition-colors font-medium">
                                <Save size={18} />
                                Save Changes
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Rename Dialog */}
            {renameCategory && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
                    <div className="bg-[#1a1a1a] border border-white/20 rounded-2xl w-full max-w-md shadow-2xl animate-in fade-in zoom-in duration-200">
                        <div className="flex justify-between items-center p-6 border-b border-white/10">
                            <h3 className="text-lg font-bold text-white">Rename Category</h3>
                            <button onClick={() => setRenameCategory(null)} className="text-white/40 hover:text-white">
                                <X size={20} />
                            </button>
                        </div>
                        <div className="p-6 space-y-4">
                            <div className="p-4 bg-orange-500/10 border border-orange-500/20 rounded-xl text-orange-200 text-sm">
                                This will rename the physical folder on disk:
                                <div className="mt-2 font-mono break-all opacity-80 text-left">
                                    {renameCategory.parent_path}/{renameCategory.folder_name} → {renameCategory.parent_path}/{newName}
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-white/60 mb-1.5 text-left">New Folder Name</label>
                                <input
                                    type="text"
                                    value={newName}
                                    onChange={(e) => setNewName(e.target.value)}
                                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
                                    autoFocus
                                />
                            </div>
                            {renameResult && (
                                <div className={`p-4 rounded-xl text-sm ${renameResult.status === 'success' ? 'bg-success/10 text-success' : 'bg-destructive/10 text-destructive'
                                    }`}>
                                    {renameResult.status === 'success' ? `Success! Renamed to ${renameResult.new_path}` : `Error: ${renameResult.message || renameResult.reason}`}
                                </div>
                            )}
                        </div>
                        <div className="flex justify-end gap-3 p-6 border-t border-white/10">
                            <button onClick={() => setRenameCategory(null)} className="px-4 py-2 text-white/60 hover:text-white transition-colors">Close</button>
                            <button
                                onClick={handleRenameSubmit}
                                disabled={renaming || !newName || newName === renameCategory.folder_name || renameResult?.status === 'success'}
                                className="px-6 py-2 bg-destructive hover:bg-destructive/90 text-white rounded-xl transition-colors font-medium disabled:opacity-50"
                            >
                                {renaming ? "Renaming..." : "Confirm Rename"}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Create Dialog */}
            {createDialogOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
                    <div className="bg-[#1a1a1a] border border-white/20 rounded-2xl w-full max-w-lg shadow-2xl animate-in fade-in zoom-in duration-200 max-h-[90vh] overflow-y-auto">
                        <div className="flex justify-between items-center p-6 border-b border-white/10 sticky top-0 bg-[#1a1a1a] z-10">
                            <h3 className="text-lg font-bold text-white">Add New Category</h3>
                            <button onClick={() => setCreateDialogOpen(false)} className="text-white/40 hover:text-white">
                                <X size={20} />
                            </button>
                        </div>
                        <div className="p-6 space-y-4">
                            {createError && (
                                <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-xl text-destructive text-sm flex items-center gap-3">
                                    <AlertCircle size={18} />
                                    <span>{createError}</span>
                                </div>
                            )}
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div className="sm:col-span-2">
                                    <label className="block text-sm font-medium text-white/60 mb-1.5 text-left">Category ID (unique_slug)</label>
                                    <input
                                        type="text"
                                        value={newCategory.id}
                                        onChange={(e) => setNewCategory({ ...newCategory, id: e.target.value })}
                                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
                                        placeholder="e.g. creative_writing"
                                    />
                                    <p className="mt-1 text-xs text-white/40">Lowercase + underscores</p>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-white/60 mb-1.5 text-left">Display Name</label>
                                    <input
                                        type="text"
                                        value={newCategory.display_name}
                                        onChange={(e) => setNewCategory({ ...newCategory, display_name: e.target.value })}
                                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
                                        placeholder="Creative Writing"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-white/60 mb-1.5 text-left">Folder Name</label>
                                    <input
                                        type="text"
                                        value={newCategory.folder_name}
                                        onChange={(e) => setNewCategory({ ...newCategory, folder_name: e.target.value })}
                                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
                                        placeholder="Creative_Writing"
                                    />
                                </div>
                                <div className="sm:col-span-2">
                                    <label className="block text-sm font-medium text-white/60 mb-1.5 text-left">Parent Path (optional)</label>
                                    <input
                                        type="text"
                                        value={newCategory.parent_path}
                                        onChange={(e) => setNewCategory({ ...newCategory, parent_path: e.target.value })}
                                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
                                        placeholder="e.g. Projects/Writing"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-white/60 mb-1.5 text-left">Aliases</label>
                                    <input
                                        type="text"
                                        value={newCategory.aliases}
                                        onChange={(e) => setNewCategory({ ...newCategory, aliases: e.target.value })}
                                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-white/60 mb-1.5 text-left">Keywords</label>
                                    <input
                                        type="text"
                                        value={newCategory.keywords}
                                        onChange={(e) => setNewCategory({ ...newCategory, keywords: e.target.value })}
                                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary/50"
                                    />
                                </div>
                            </div>
                        </div>
                        <div className="flex justify-end gap-3 p-6 border-t border-white/10 sticky bottom-0 bg-[#1a1a1a] z-10">
                            <button onClick={() => setCreateDialogOpen(false)} className="px-4 py-2 text-white/60 hover:text-white transition-colors">Cancel</button>
                            <button
                                onClick={handleCreateSubmit}
                                disabled={creating || !newCategory.id || !newCategory.display_name || !newCategory.folder_name}
                                className="px-6 py-2 bg-primary hover:bg-primary/90 text-white rounded-xl transition-colors font-medium"
                            >
                                {creating ? "Creating..." : "Create Category"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
