/**
 * Google Cloud Storage Service
 * Provides functions to list files and get content from GCS buckets.
 */

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
