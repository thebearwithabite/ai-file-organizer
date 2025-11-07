/**
 * TypeScript types for API responses
 */

export interface SystemStatus {
  google_drive: {
    connected: boolean
    user_name: string
    sync_status: string
    last_sync: string
  }
  disk_space: {
    free_gb: number
    total_gb: number
    percent_used: number
    status: 'safe' | 'warning' | 'critical'
  }
  background_services: {
    adaptive_monitor: string
    staging_monitor: string
    drive_sync: string
  }
  confidence_mode: string
}

export interface LearningStats {
  files_organized_today: number
  patterns_count: number
  confidence_mode: string
  searches_today: number
}

export interface FileOperation {
  operation_id: number
  timestamp: string
  operation_type: string
  file_name: string
  new_path?: string
}

export interface ClassificationResult {
  file_id: string
  file_name: string
  classification: {
    category: string
    confidence: number
    reasoning: string
    needs_review: boolean
  }
  status: string
  destination_path: string
  operation_id: number
}

export interface RollbackOperation {
  operation_id: number
  timestamp: string
  operation_type: string
  original_filename: string
  new_filename: string
  original_path: string
  new_location: string
  confidence: number
  status: string
  notes: string
  google_drive_id?: string
}

export type ConfidenceMode = 'never' | 'minimal' | 'smart' | 'always'

export interface ConfidenceModeResponse {
  mode: ConfidenceMode
}

export interface SpaceProtectionStatus {
  used_percent: number
  free_gb: number
  total_gb: number
  threshold_85: boolean
  threshold_95: boolean
  status: 'healthy' | 'warning' | 'critical'
}

export interface DuplicateGroup {
  group_id: string
  files: {
    path: string
    size: number
    modified: string
  }[]
  total_size: number
}

export interface DuplicatesResponse {
  groups: DuplicateGroup[]
}

export interface MonitorStatus {
  status: 'active' | 'paused'
  paths: string[]
  last_event: string | null
  events_processed: number
  uptime_seconds: number
}
