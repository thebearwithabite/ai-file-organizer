
const API_BASE = '';

export interface Category {
    id: string;
    display_name: string;
    folder_name: string;
    parent_path: string;
    path_fingerprint: string;
    locked: boolean;
    aliases: string[];
    keywords: string[];
    extensions: string[];
    confidence: number;
}

export interface CategoryUpdate {
    display_name?: string;
    aliases?: string[];
    keywords?: string[];
    extensions?: string[];
    locked?: boolean;
}

export interface RenameRequest {
    new_name: string;
}

export interface RenameResult {
    status: 'success' | 'blocked' | 'skipped' | 'error';
    old_path?: string;
    new_path?: string;
    reason?: string;
    conflict_category_id?: string;
    message?: string;
}

export const taxonomyService = {
    // Create new category
    createCategory: async (category: Partial<Category>): Promise<Category> => {
        const response = await fetch(`${API_BASE}/api/taxonomy/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(category)
        });
        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Failed to create category: ${error}`);
        }
        const data = await response.json();
        return data.category;
    },

    // Get all categories
    getTaxonomy: async (): Promise<Record<string, Category>> => {
        const response = await fetch(`${API_BASE}/api/taxonomy/`);
        if (!response.ok) throw new Error('Failed to fetch taxonomy');
        return response.json();
    },

    // Get single category
    getCategory: async (categoryId: string): Promise<Category> => {
        const response = await fetch(`${API_BASE}/api/taxonomy/${categoryId}`);
        if (!response.ok) throw new Error('Failed to fetch category');
        return response.json();
    },

    // Update metadata (aliases, keywords)
    updateCategory: async (categoryId: string, updates: CategoryUpdate): Promise<Category> => {
        const response = await fetch(`${API_BASE}/api/taxonomy/${categoryId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        });
        if (!response.ok) throw new Error('Failed to update category');
        const data = await response.json();
        return data.category; // API returns { status: "success", category: ... }
    },

    // Rename category (and folder)
    renameCategory: async (categoryId: string, newName: string): Promise<RenameResult> => {
        const response = await fetch(`${API_BASE}/api/taxonomy/${categoryId}/rename`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ new_name: newName })
        });

        // Handle 409 Conflict specifically (Business Logic Block)
        if (response.status === 409) {
            const error = await response.json();
            return error.detail; // Backend returns the RenameResult in detail
        }

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Rename failed: ${error}`);
        }

        return response.json();
    }
};
