
import React, { useState, useEffect } from 'react';
import {
    Box,
    Typography,
    Paper,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Chip,
    IconButton,
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    TextField,
    Alert,
    Tooltip,
    CircularProgress
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DriveFileRenameOutlineIcon from '@mui/icons-material/DriveFileRenameOutline';
import LockIcon from '@mui/icons-material/Lock';

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

    // --- Format Helpers ---
    const formatList = (list: string[]) => list.join(', ');

    // --- Edit Handlers ---
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
            // Ideally show snackbar
        }
    };

    // --- Rename Handlers ---
    const handleRenameOpen = (cat: Category) => {
        if (cat.locked) return; // Should be disabled in UI anyway
        setRenameCategory(cat);
        setNewName(cat.folder_name); // Default to current folder name
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
                // Wait briefly then reload
                setTimeout(() => {
                    loadTaxonomy();
                    setRenameCategory(null); // Close on success? Or show success msg?
                    // Let's keep open to show success result, user closes manually
                }, 1000);
            }
        } catch (err: any) {
            setRenameResult({ status: 'error', message: err.message });
        } finally {
            setRenaming(false);
        }
    };

    // --- Create Handlers ---
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

    if (loading) return <CircularProgress />;
    if (error) return <Alert severity="error">{error}</Alert>;

    return (
        <Box>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">Category Management (Taxonomy V3)</Typography>
                <Button variant="contained" color="primary" onClick={handleCreateOpen}>
                    Add New Category
                </Button>
            </Box>
            <Alert severity="info" sx={{ mb: 2 }}>
                Changes here affect the AI's classification logic and the physical folder structure.
                Renaming a category will rename its folder on disk.
            </Alert>

            <TableContainer component={Paper}>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>Display Name</TableCell>
                            <TableCell>Folder Path</TableCell>
                            <TableCell>Keywords</TableCell>
                            <TableCell>Aliases</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {Object.values(categories).map((cat) => (
                            <TableRow key={cat.id}>
                                <TableCell>
                                    <Box display="flex" alignItems="center" gap={1}>
                                        {cat.display_name}
                                        {cat.locked && <Tooltip title="Locked System Category"><LockIcon fontSize="small" color="action" /></Tooltip>}
                                    </Box>
                                </TableCell>
                                <TableCell>
                                    <Chip
                                        label={`${cat.parent_path ? cat.parent_path + '/' : ''}${cat.folder_name}`}
                                        size="small"
                                        variant="outlined"
                                        sx={{ fontFamily: 'monospace' }}
                                    />
                                </TableCell>
                                <TableCell sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    {cat.keywords?.join(', ')}
                                </TableCell>
                                <TableCell sx={{ maxWidth: 150 }}>
                                    {cat.aliases?.join(', ')}
                                </TableCell>
                                <TableCell align="right">
                                    <IconButton size="small" onClick={() => handleEditOpen(cat)} disabled={cat.locked}>
                                        <EditIcon fontSize="small" />
                                    </IconButton>
                                    <Tooltip title="Rename Category & Folder">
                                        <span>
                                            <IconButton size="small" onClick={() => handleRenameOpen(cat)} disabled={cat.locked}>
                                                <DriveFileRenameOutlineIcon fontSize="small" />
                                            </IconButton>
                                        </span>
                                    </Tooltip>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>

            {/* Edit Modal */}
            <Dialog open={!!editCategory} onClose={() => setEditCategory(null)}>
                <DialogTitle>Edit Metadata: {editCategory?.display_name}</DialogTitle>
                <DialogContent>
                    <TextField
                        fullWidth
                        margin="dense"
                        label="Aliases (comma separated)"
                        value={editAliases}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditAliases(e.target.value)}
                        helperText="Alternative names for this category (e.g. 'Snaps', 'Pics')"
                    />
                    <TextField
                        fullWidth
                        margin="dense"
                        label="Keywords (comma separated)"
                        value={editKeywords}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditKeywords(e.target.value)}
                        helperText="Strong keywords that trigger this category"
                    />
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setEditCategory(null)}>Cancel</Button>
                    <Button onClick={handleEditSave} variant="contained" color="primary">Save</Button>
                </DialogActions>
            </Dialog>

            {/* Rename Dialog */}
            <Dialog open={!!renameCategory} onClose={() => setRenameCategory(null)}>
                <DialogTitle>Rename Category</DialogTitle>
                <DialogContent>
                    <Alert severity="warning" sx={{ mb: 2 }}>
                        This will rename the physical folder on disk:
                        <br />
                        <b>{renameCategory?.parent_path}/{renameCategory?.folder_name}</b> → <b>{renameCategory?.parent_path}/{newName}</b>
                    </Alert>

                    <TextField
                        fullWidth
                        label="New Folder Name"
                        value={newName}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewName(e.target.value)}
                        autoFocus
                    />

                    {renameResult && (
                        <Box mt={2}>
                            {renameResult.status === 'success' && (
                                <Alert severity="success">Success! Renamed to {renameResult.new_path}</Alert>
                            )}
                            {renameResult.status === 'blocked' && (
                                <Alert severity="error">
                                    Blocked: {renameResult.reason}
                                    {renameResult.conflict_category_id && ` (Conflict: ${renameResult.conflict_category_id})`}
                                </Alert>
                            )}
                            {renameResult.status === 'error' && (
                                <Alert severity="error">Error: {renameResult.message}</Alert>
                            )}
                        </Box>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setRenameCategory(null)}>Close</Button>
                    <Button
                        onClick={handleRenameSubmit}
                        variant="contained"
                        color="error"
                        disabled={renaming || !newName || newName === renameCategory?.folder_name || renameResult?.status === 'success'}
                    >
                        {renaming ? "Renaming..." : "Confirm Rename"}
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Create Dialog */}
            <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
                <DialogTitle>Add New Category</DialogTitle>
                <DialogContent>
                    {createError && <Alert severity="error" sx={{ mb: 2 }}>{createError}</Alert>}
                    <Box display="flex" flexDirection="column" gap={2} mt={1}>
                        <TextField
                            label="Category ID (unique_slug)"
                            value={newCategory.id}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewCategory({ ...newCategory, id: e.target.value })}
                            helperText="Used internally, lowercase + underscores (e.g. creative_writing)"
                        />
                        <TextField
                            label="Display Name"
                            value={newCategory.display_name}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewCategory({ ...newCategory, display_name: e.target.value })}
                            helperText="Human readable name in the UI"
                        />
                        <TextField
                            label="Folder Name"
                            value={newCategory.folder_name}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewCategory({ ...newCategory, folder_name: e.target.value })}
                            helperText="Actual folder name on disk"
                        />
                        <TextField
                            label="Parent Path (optional)"
                            value={newCategory.parent_path}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewCategory({ ...newCategory, parent_path: e.target.value })}
                            helperText="Folder group (e.g. Visual_Assets)"
                        />
                        <TextField
                            label="Aliases (comma separated)"
                            value={newCategory.aliases}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewCategory({ ...newCategory, aliases: e.target.value })}
                        />
                        <TextField
                            label="Keywords (comma separated)"
                            value={newCategory.keywords}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewCategory({ ...newCategory, keywords: e.target.value })}
                        />
                    </Box>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
                    <Button
                        onClick={handleCreateSubmit}
                        variant="contained"
                        disabled={creating || !newCategory.id || !newCategory.display_name || !newCategory.folder_name}
                    >
                        {creating ? "Creating..." : "Create Category"}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};
