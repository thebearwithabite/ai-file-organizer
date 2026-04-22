/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export const AppState = {
    IDLE: 'IDLE',
    LOADING: 'LOADING',
    SUCCESS: 'SUCCESS',
    ERROR: 'ERROR',
} as const;
export type AppState = typeof AppState[keyof typeof AppState];

export const ShotStatus = {
    PENDING_JSON: 'PENDING_JSON',
    GENERATING_JSON: 'GENERATING_JSON',
    PENDING_KEYFRAME_PROMPT: 'PENDING_KEYFRAME_PROMPT',
    GENERATING_KEYFRAME_PROMPT: 'GENERATING_KEYFRAME_PROMPT',
    NEEDS_KEYFRAME_GENERATION: 'NEEDS_KEYFRAME_GENERATION',
    GENERATING_IMAGE: 'GENERATING_IMAGE',
    NEEDS_REVIEW: 'NEEDS_REVIEW',
    APPROVED: 'APPROVED',
    GENERATION_FAILED: 'GENERATION_FAILED',
} as const;
export type ShotStatus = typeof ShotStatus[keyof typeof ShotStatus];

export const VeoStatus = {
    IDLE: 'IDLE',
    QUEUED: 'QUEUED',
    GENERATING: 'GENERATING',
    COMPLETED: 'COMPLETED',
    FAILED: 'FAILED',
} as const;
export type VeoStatus = typeof VeoStatus[keyof typeof VeoStatus];

export const LogType = {
    INFO: 'INFO',
    SUCCESS: 'SUCCESS',
    ERROR: 'ERROR',
    STEP: 'STEP',
} as const;
export type LogType = typeof LogType[keyof typeof LogType];

export interface LogEntry {
    timestamp: string;
    message: string;
    type: LogType;
}

export interface VeoShot {
    shot_id: string;
    scene: {
        context: string;
        visual_style: string;
        lighting: string;
        mood: string;
        aspect_ratio: '16:9' | '9:16';
        duration_s: 4 | 6 | 8;
    };
    character: {
        name: string;
        gender_age: string;
        description_lock: string;
        behavior: string;
        expression: string;
    };
    camera: {
        shot_call: string;
        movement: string;
    };
    audio: {
        dialogue: string;
        delivery: string;
        ambience?: string;
        sfx?: string;
    };
    flags: {
        continuity_lock: boolean;
        do_not: string[];
        anti_artifacts: string[];
        conflicts: string[];
        warnings: string[];
        cv_updates: string[];
    };
}

export interface VeoShotWrapper {
    unit_type: 'shot' | 'extend';
    directorNotes?: string;
    veo_shot: VeoShot;
}

export interface IngredientImage {
    base64: string;
    mimeType: string;
}

export type AssetType = 'character' | 'location' | 'prop' | 'style';

export interface ProjectAsset {
    id: string;
    name: string;
    description: string;
    type: AssetType;
    image: IngredientImage | null;
    vault_fingerprint?: string;
    visual_anchors?: string[];
    semantic_tags?: string[];
    episode_id?: string;
    project_slug?: string;
}

export interface Shot {
    id: string;
    status: ShotStatus;
    pitch: string;
    sceneName?: string;
    veoJson?: VeoShotWrapper;
    keyframePromptText?: string;
    keyframeImage?: string;
    errorMessage?: string;
    selectedAssetIds: string[];
    veoTaskId?: string;
    veoStatus?: VeoStatus;
    veoVideoUrl?: string;
    veoError?: string;
    veoReferenceUrl?: string;
    isApproved?: boolean;
    veoUseKeyframeAsReference?: boolean;
}

export type ShotBook = Shot[];
