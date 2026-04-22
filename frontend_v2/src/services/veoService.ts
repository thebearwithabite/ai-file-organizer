/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

// Types for Veo API
export interface VeoGenerateRequest {
    prompt: string;
    model: 'veo3_fast';
    aspectRatio?: '16:9' | '9:16' | 'Auto';
    generationType?: 'TEXT_2_VIDEO' | 'FIRST_AND_LAST_FRAMES_2_VIDEO' | 'REFERENCE_2_VIDEO';
    imageUrls?: string[];
    seeds?: number;
    watermark?: string;
    enableTranslation?: boolean;
}

export interface VeoExtendRequest {
    taskId: string;
    prompt: string;
    seeds?: number;
    watermark?: string;
    callBackUrl?: string;
}

export interface VeoGenerateResponse {
    code: number;
    msg: string;
    data: {
        taskId: string;
    };
}

export interface VeoTaskInfoResponse {
    code: number;
    msg: string;
    data: {
        taskId: string;
        successFlag: 0 | 1 | 2 | 3; // 0: Generating, 1: Success, 2: Failed, 3: Generation Failed
        errorMessage?: string;
        fallbackFlag?: boolean;
        response?: {
            resultUrls?: string[];
            resolution?: string;
            originUrls?: string[];
        }
    }
}

// Proxies through our Python backend to avoid exposing API keys on client if possible,
// OR allows direct call if backend is bypassing.
// Since the python backend now has /api/veo/video/generate, we should point there?
// However, the user's provided code for this file pointed to https://api.kie.ai
// But the user ALSO approved my plan to make a Python Proxy.
// So I will make this service call MY FastApi endpoints.

const API_BASE = '/api/veo/video';

/**
 * Generates a video using Veo 3.1 via Python Proxy
 */
export const generateVeoVideo = async (apiKey: string, params: VeoGenerateRequest): Promise<VeoGenerateResponse> => {
    // apiKey argument is kept for compatibility with user's hook, but backend might use env var.
    // Actually, the new frontend code passes 'veoApiKey' state.
    // If we use the proxy, we can ignore it on the client side or pass it in header if dynamic.
    // My proxy uses `KIE_API_KEY` env var.
    // But maybe I should allow passing it if the user wants to bring their own key?
    // For now, I'll point to my backend endpoint.

    const response = await fetch(`${API_BASE}/generate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            // 'X-Kie-Token': apiKey // Optional if we want to support client-side key
        },
        body: JSON.stringify(params)
    });

    if (!response.ok) {
        throw new Error(`Veo API Error: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
};

/**
 * Extends an existing Veo 3.1 video
 */
export const extendVeoVideo = async (apiKey: string, params: VeoExtendRequest): Promise<VeoGenerateResponse> => {
    const response = await fetch(`${API_BASE}/extend`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(params)
    });

    if (!response.ok) {
        throw new Error(`Veo Extend Error: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
};

/**
 * Checks the status of a Veo generation task
 */
export const getVeoTaskDetails = async (apiKey: string, taskId: string): Promise<VeoTaskInfoResponse> => {
    const response = await fetch(`${API_BASE}/status/${taskId}`, {
        method: 'GET'
    });

    // Handle 503 if backend key is missing
    if (response.status === 503) {
        throw new Error("Video service unavailable (Missing API Key on backend)");
    }

    const data = await response.json();
    return data as VeoTaskInfoResponse;
};
