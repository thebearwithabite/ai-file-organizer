/**
 * Real API Service - Connects to FastAPI Backend
 * Backend runs on http://localhost:8000
 */

import type { SystemStatus, LearningStats, FileOperation, ClassificationResult } from '../types/api'

const API_BASE = 'http://localhost:8000'

export const api = {
  getSystemStatus: async (): Promise<SystemStatus> => {
    const response = await fetch(`${API_BASE}/api/system/status`)
    if (!response.ok) throw new Error('Failed to fetch system status')
    
    const data = await response.json()
    
    // Transform backend response to frontend format
    return {
      google_drive: {
        connected: data.authentication_status === 'authenticated',
        user_name: data.google_drive_user || 'Unknown',
        sync_status: data.sync_service_status || 'disabled',
        last_sync: data.last_run || new Date().toISOString(),
      },
      disk_space: data.disk_space || {
        free_gb: 0,
        total_gb: 0,
        percent_used: 0,
        status: 'unknown'
      },
      background_services: {
        adaptive_monitor: 'stopped',
        staging_monitor: 'stopped',
        drive_sync: data.sync_service_status || 'disabled',
      },
      confidence_mode: 'smart', // TODO: Get from backend
    }
  },

  getLearningStats: async (): Promise<LearningStats> => {
    // TODO: Implement backend endpoint for learning stats
    return {
      files_organized_today: 0,
      patterns_count: 0,
      confidence_mode: 'SMART',
      searches_today: 0,
    }
  },

  getRecentOperations: async (): Promise<FileOperation[]> => {
    // TODO: Implement backend endpoint for recent operations
    return []
  },

  uploadFile: async (file: File): Promise<ClassificationResult> => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${API_BASE}/api/triage/upload`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`File upload failed: ${error}`)
    }

    return await response.json()
  },

  updateConfidenceMode: async (mode: string) => {
    // TODO: Implement backend endpoint
    return { success: true, mode }
  },

  emergencyCleanup: async () => {
    const response = await fetch(`${API_BASE}/api/system/emergency_cleanup`, {
      method: 'POST',
    })

    if (!response.ok) throw new Error('Emergency cleanup failed')

    return await response.json()
  },

  getRollbackOperations: async (params?: { days?: number; todayOnly?: boolean; search?: string }) => {
    const searchParams = new URLSearchParams()
    if (params?.days) searchParams.append('days', params.days.toString())
    if (params?.todayOnly) searchParams.append('today_only', 'true')
    if (params?.search) searchParams.append('search', params.search)

    const response = await fetch(`${API_BASE}/api/rollback/operations?${searchParams}`)
    if (!response.ok) throw new Error('Failed to fetch rollback operations')

    return await response.json()
  },

  undoOperation: async (operationId: number) => {
    const response = await fetch(`${API_BASE}/api/rollback/undo/${operationId}`, {
      method: 'POST',
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to undo operation')
    }

    return await response.json()
  },

  undoToday: async () => {
    const response = await fetch(`${API_BASE}/api/rollback/undo-today`, {
      method: 'POST',
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to undo today\'s operations')
    }

    return await response.json()
  },

  classifyFile: async (filePath: string, confirmedCategory: string, project?: string, episode?: string) => {
    const response = await fetch(`${API_BASE}/api/triage/classify`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        file_path: filePath,
        confirmed_category: confirmedCategory,
        project: project || null,
        episode: episode || null,
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to classify file')
    }

    return await response.json()
  },

  getFilesForReview: async () => {
    const response = await fetch(`${API_BASE}/api/triage/files_to_review`)
    if (!response.ok) throw new Error('Failed to fetch files for review')
    return await response.json()
  },

  triggerTriageScan: async () => {
    const response = await fetch(`${API_BASE}/api/triage/trigger_scan`, {
      method: 'POST',
    })
    if (!response.ok) throw new Error('Failed to trigger scan')
    return await response.json()
  },

  scanCustomFolder: async (folderPath: string) => {
    const response = await fetch(`${API_BASE}/api/triage/scan_folder`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        folder_path: folderPath,
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to scan folder')
    }

    return await response.json()
  },

  searchFiles: async (query: string) => {
    const response = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}`)
    if (!response.ok) throw new Error('Failed to search files')
    return await response.json()
  },

  openFile: async (filePath: string) => {
    const response = await fetch(`${API_BASE}/api/open-file`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        path: filePath,
      }),
    })
    if (!response.ok) throw new Error('Failed to open file')
    return await response.json()
  },
}
