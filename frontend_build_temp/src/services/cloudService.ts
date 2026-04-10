/**
 * Google Cloud Storage Service
 * Provides functions to list files and get content from GCS buckets.
 */

export const DEFAULT_BUCKET = 'aether-studio-vault-mock';

export const listFiles = async (accessToken: string, bucketName: string, prefix: string = '') => {
    const url = `https://storage.googleapis.com/storage/v1/b/${bucketName}/o?prefix=${encodeURIComponent(prefix)}`;

    const response = await fetch(url, {
        headers: {
            'Authorization': `Bearer ${accessToken}`
        }
    });

    if (!response.ok) {
        const error = await response.json();
        console.error('GCS List Files Error:', error);
        throw new Error(error.error?.message || 'Failed to list files from GCS');
    }

    const data = await response.json();
    return data.items || [];
};

export const getFileContent = async (fileName: string, accessToken: string, bucketName: string) => {
    const url = `https://storage.googleapis.com/storage/v1/b/${bucketName}/o/${encodeURIComponent(fileName)}?alt=media`;

    const response = await fetch(url, {
        headers: {
            'Authorization': `Bearer ${accessToken}`
        }
    });

    if (!response.ok) {
        const error = await response.text();
        console.error('GCS Get File Error:', error);
        throw new Error('Failed to retrieve file content from GCS');
    }

    return await response.text();
};


export const uploadToGCS = async (path: string, _contentBase64: string, contentType: string, __token: string) => {
    console.log(`[CloudService] Uploading to ${path} (${contentType})`);
    // Mock upload - TODO: Implement real upload
    return `https://storage.googleapis.com/${DEFAULT_BUCKET}/${path}`;
};

export const getAccessTokenFromServiceAccount = async (_key: any) => {
    return { access_token: "mock_gcp_token", expires_in: 3600 };
};

export const fetchSecretKey = async (_token: string) => {
    // Return a mock API key or instruct user to use env
    return "mock_api_key_use_env_instead";
};

export const listProjectsFromVault = async (_token: string) => {
    return ["Mock Project A", "Mock Project B"];
};

export const vaultAssetToLibrary = async (_type: string, name: string, _base64: string, _metadata: any, _token: string) => {
    console.log(`[CloudService] Vaulting asset: ${name}`);
};

export const legacyProjectInstaller = async (_slug: string, _token: string) => {
    throw new Error("Legacy installer not supported in local mode.");
};

export const updateWorldRegistry = async (_token: string, data: any) => {
    console.log(`[CloudService] Updating World Registry:`, data);
};

export const proxyVeoToVault = async (url: string, _projectName: string, _shotId: string, _token: string) => {
    return url;
};
