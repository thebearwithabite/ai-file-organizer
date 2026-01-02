/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export const DEFAULT_BUCKET = 'aether-studio-vault-mock';

export const uploadToGCS = async (path: string, contentBase64: string, contentType: string, token: string) => {
    console.log(`[CloudService] Uploading to ${path} (${contentType})`);
    // Mock upload
    return `https://storage.googleapis.com/${DEFAULT_BUCKET}/${path}`;
};

export const getAccessTokenFromServiceAccount = async (key: any) => {
    return { access_token: "mock_gcp_token", expires_in: 3600 };
};

export const fetchSecretKey = async (token: string) => {
    // Return a mock API key or instruct user to use env
    return "mock_api_key_use_env_instead";
};

export const listProjectsFromVault = async (token: string) => {
    return ["Mock Project A", "Mock Project B"];
};

export const vaultAssetToLibrary = async (type: string, name: string, base64: string, metadata: any, token: string) => {
    console.log(`[CloudService] Vaulting asset: ${name}`);
};

export const legacyProjectInstaller = async (slug: string, token: string) => {
    throw new Error("Legacy installer not supported in local mode.");
};

export const updateWorldRegistry = async (token: string, data: any) => {
    console.log(`[CloudService] Updating World Registry:`, data);
};

export const proxyVeoToVault = async (url: string, projectName: string, shotId: string, token: string) => {
    return url;
};
