export interface Identity {
    id: string;
    name: string;
    type: string;
    description?: string;
    priority: number;
}

export interface IdentityUpdate {
    name?: string;
    type?: string;
    description?: string;
    priority?: number;
}

export interface IdentitySummary {
    total: number;
    by_type: Record<string, number>;
}

const API_BASE = '/api/identities';

export const identityService = {
    async getIdentities(): Promise<Identity[]> {
        const response = await fetch(API_BASE);
        if (!response.ok) throw new Error('Failed to fetch identities');
        return response.json();
    },

    async getIdentity(id: string): Promise<Identity> {
        const response = await fetch(`${API_BASE}/${id}`);
        if (!response.ok) throw new Error('Failed to fetch identity');
        return response.json();
    },

    async createIdentity(identity: Identity): Promise<Identity> {
        const response = await fetch(API_BASE, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(identity),
        });
        if (!response.ok) throw new Error('Failed to create identity');
        return response.json();
    },

    async updateIdentity(id: string, update: IdentityUpdate): Promise<Identity> {
        const response = await fetch(`${API_BASE}/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(update),
        });
        if (!response.ok) throw new Error('Failed to update identity');
        return response.json();
    },

    async deleteIdentity(id: string): Promise<void> {
        const response = await fetch(`${API_BASE}/${id}`, {
            method: 'DELETE',
        });
        if (!response.ok) throw new Error('Failed to delete identity');
    },

    async getSummary(): Promise<IdentitySummary> {
        const response = await fetch(`${API_BASE}/stats/summary`);
        if (!response.ok) throw new Error('Failed to fetch identity summary');
        return response.json();
    }
};
