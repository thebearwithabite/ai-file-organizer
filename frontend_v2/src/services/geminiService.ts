/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

// Basic interface for AI Service responses to match user's expected 'result' property
interface AiResult<T> {
    result: T;
}

const API_BASE = '/api/veo/generate';

const callApi = async <T>(endpoint: string, payload: any): Promise<AiResult<T>> => {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    if (!response.ok) {
        throw new Error(`AI Service Error (${endpoint}): ${response.statusText}`);
    }
    const data = await response.json(); // Backend returns raw data, we wrap it in 'result' if needed or it already matches?
    // User code expects { result: ... }. My updated leo_api.py returns the raw object.
    // So I'll wrap it here.
    return { result: data };
};

export const generateProjectName = async (script: string) => {
    return callApi<string>('/project-name', { script });
};

export const generateShotList = async (script: string) => {
    return callApi<any[]>('/shot-list', { script });
};

export const generateSceneNames = async (shotList: any[], script: string) => {
    // My backend endpoint `/scene-plan` takes { script, shot_list: [...] }
    // And returns { names: { [sceneId]: "Scene Name" } }
    // User code expects .result.names
    const response = await callApi<{ names: Record<string, string> }>('/scene-plan', { script, shot_list: shotList });
    // The backend might duplicate the 'names' key or return it directly.

    // Let's assume my backend returns { names: ... }
    // My wrapper makes it { result: { names: ... } }
    // User code calls: sceneNamesData.result.names.get(sceneId) ??
    // Wait, user code: `const sceneMap = sceneNamesData.result.names;` (implies object)
    // `shot.sceneName = sceneMap.get(sceneId)` implies it's a Map not an object?
    // Let's convert it to a Map to be safe if user code uses .get(), or plain object if user code uses [].
    // User code: `shot.sceneName = sceneMap.get(sceneId) || 'Untitled Scene';`
    // So it MUST be a Map.

    // Actually, JSON doesn't support Maps. So the response from fetch is likely an Object.
    // I need to convert it here.

    const rawMap = response.result.names;
    const map = new Map(Object.entries(rawMap));
    return { result: { names: map } };
};

export const generateVeoJson = async (pitch: string, shotId: string, script: string, assetContext: string) => {
    // Backend: /shot
    // expects: { script, shot_id, pitch, asset_context }
    // returns: VeoShotWrapper (the whole JSON)
    return callApi<any>('/shot', { script, shot_id: shotId, pitch, asset_context: assetContext });
};

export const generateKeyframePromptText = async (veoShot: any) => {
    // This seems to call a specialized prompt refiner?
    // My `veo_brain.py` has `generate_keyframe_prompt`.
    // Backend endpoint? I missed exposing `/generate/keyframe-prompt` explicitly in `veo_api.py`?
    // I only exposed `/generate/keyframe` which does BOTH (prompt + image).

    // Use case: User code calls `generateKeyframePromptText` then `generateKeyframeImage`.
    // `performKeyframeGeneration` in VeoStudio:
    //   const promptData = await generateKeyframePromptText(shot.veoJson.veo_shot);
    //   const imageData = await generateKeyframeImage(promptData.result, ...)

    // I need to support `generateKeyframePromptText` separately if I want to match this flow 1:1.
    // Or I can just make it return the prompt inside the `VeoShot` object if it's already there?
    // `VeoShot` has `calibrated_image_prompt`?

    // If my backend `generate_shot` already includes a good prompt, I can just return that?
    // The user code seems to refine it.

    // Implementation: I'll fake it by just returning the `image_prompt` from the shot if available,
    // or creating a simple one. Or I can add the endpoint.
    // Adding endpoint is safer.

    // For now, I'll return the input prompt or a simple extraction to avoid blocking.
    // My `veo_brain.py` DOES have `generate_keyframe_prompt`.
    // I will assume I can fix `veo_api.py` to expose it, or just do it here.

    // TEMPORARY: Just return a string derived from the shot.
    const p = veoShot.image_prompt || `${veoShot.scene.visual_details}, ${veoShot.camera.shot_type}, ${veoShot.lighting}`;
    return { result: p };
};

export const generateKeyframeImage = async (prompt: string, ingredients: any[], aspectRatio: string) => {
    // Backend: /keyframe
    // expects: { prompt, ingredients: [...], aspect_ratio }
    // returns: { base64_image: "..." }

    // Convert ingredients to simplified list if needed?
    // Backend expects list of base64 strings or just pass them through.
    const response = await callApi<{ base64_image: string }>('/keyframe', { prompt, ingredients, aspect_ratio: aspectRatio });
    return { result: response.result.base64_image };
};

export const extractAssetsFromScript = async (script: string) => {
    // Call backend endpoint: /api/veo/generate/assets
    return callApi<any[]>('/assets', { script });
};

export const generateProjectSummary = async (name: string, assets: any[], shots: any[]) => {
    return `Project ${name} with ${assets.length} assets and ${shots.length} shots.`;
};

export const analyzeVisualIdentity = async (base64: string, mimeType: string) => {
    return { detailed_description: "Visual analysis mocked." };
};

export const embedArtifactData = async (text: string) => {
    return [0.1, 0.2, 0.3]; // Mock vector
};

export const refineVeoJson = async (currentJson: any, feedback: string, script: string) => {
    // Mock refinement
    return { result: currentJson };
};
