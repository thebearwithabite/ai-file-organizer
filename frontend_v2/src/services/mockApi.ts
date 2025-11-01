/**
 * Mock API Service for Development
 * These responses will be replaced with real API calls later
 */

import type { SystemStatus, LearningStats, FileOperation, ClassificationResult } from '../types/api'

// Simulate network delay
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

export const mockApi = {
  getSystemStatus: async (): Promise<SystemStatus> => {
    await delay(500)
    return {
      google_drive: {
        connected: true,
        user_name: 'User Thomson',
        sync_status: 'synced',
        last_sync: new Date().toISOString(),
      },
      disk_space: {
        free_gb: 10,
        total_gb: 228,
        percent_used: 59,
        status: 'warning' as const,
      },
      background_services: {
        adaptive_monitor: 'running',
        staging_monitor: 'running',
        drive_sync: 'running',
      },
      confidence_mode: 'smart',
    }
  },

  getLearningStats: async (): Promise<LearningStats> => {
    await delay(500)
    return {
      files_organized_today: 12,
      patterns_count: 247,
      confidence_mode: 'SMART',
      searches_today: 8,
    }
  },

  getRecentOperations: async (): Promise<FileOperation[]> => {
    await delay(500)
    return [
      {
        operation_id: 1,
        timestamp: new Date(Date.now() - 120000).toISOString(), // 2 min ago
        operation_type: 'organize',
        file_name: 'contract_draft.pdf',
        new_path: 'Entertainment/Contracts/Management',
      },
      {
        operation_id: 2,
        timestamp: new Date(Date.now() - 900000).toISOString(), // 15 min ago
        operation_type: 'batch',
        file_name: '8 files organized',
        new_path: 'Various categories',
      },
      {
        operation_id: 3,
        timestamp: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
        operation_type: 'organize',
        file_name: 'podcast_theme.mp3',
        new_path: 'Creative/Audio',
      },
    ]
  },

  uploadFile: async (file: File): Promise<ClassificationResult> => {
    await delay(2000) // Simulate upload delay

    // Mock classification result
    return {
      file_id: Math.random().toString(36).substr(2, 9),
      file_name: file.name,
      classification: {
        category: 'Entertainment/Contracts/Management',
        confidence: 0.87,
        reasoning: 'Detected contract-related terms and mentions of client relationships in the document content.',
        needs_review: false,
      },
      status: 'organized',
      destination_path: '/Users/user/GoogleDrive/AI_Organizer/Entertainment/Contracts/Management/' + file.name,
      operation_id: Math.floor(Math.random() * 10000),
    }
  },

  updateConfidenceMode: async (mode: string) => {
    await delay(500)
    return { success: true, mode }
  },

  emergencyCleanup: async () => {
    await delay(2000) // Simulate cleanup delay
    return {
      moved_count: 5,
      freed_mb: 1200,
      status: 'success'
    }
  },
}
