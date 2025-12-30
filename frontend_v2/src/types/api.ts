/**
 * TypeScript types for API responses
 */

export interface SystemStatus {
  backend_status?: string
  monitor?: {
    watching_paths: number
    rules_loaded: number
  }
  orchestration?: {
    last_run: string | null
    files_processed: number
    status: string
  }
  // Legacy support for existing dashboards
  google_drive?: {
    connected: boolean
    user_name: string
    sync_status: string
    last_sync: string
    drive_root?: string
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
  // Extended stats used by Settings page
  total_learning_events?: number
  image_events?: number
  video_events?: number
  audio_events?: number
  document_events?: number
  unique_categories_learned?: number
  most_common_category?: string | null
  top_confidence_average?: number
  media_type_breakdown?: Record<string, number>
  category_distribution?: Record<string, number>
}

export interface FileOperation {
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
  rules_count: number
}

export interface Category {
  id: string
  name: string
  path: string
  color: string
  description: string
}

export interface Project {
  id: string
  name: string
}

export interface ProjectsResponse {
  projects: Project[]
  count: number
}

export interface MaintenanceLog {
  task_name: string
  last_run: string
  success: boolean
  details: string
}

export interface EmergencyLog {
  timestamp: string
  emergency_type: string
  severity_level: string
  details: string
  action_taken: string
}

// ===== VEO Studio Types =====

export interface VEOAsset {
  type: 'character' | 'location' | 'prop' | 'other'
  name: string
  description?: string
  occurrences: number
}

export interface VEOScriptAnalysis {
  success: boolean
  assets: VEOAsset[]
  shot_count: number
  scene_count: number
  metadata: {
    word_count: number
    line_count: number
    analyzed_at: string
    project_name?: string
  }
  error?: string
}

export interface VEOShot {
  shot_id: string
  scene_number?: number
  shot_number: number
  description: string
  duration_estimate?: number
  camera_angle?: string
  characters: string[]
  location?: string
  assets_needed: string[]
}

export interface VEOShotList {
  success: boolean
  shots: VEOShot[]
  total_shots: number
  total_duration_estimate?: number
  error?: string
}

export interface VEOKeyframe {
  success: boolean
  keyframe_url?: string
  keyframe_path?: string
  generation_method: 'gemini' | 'flux' | 'stub'
  error?: string
}

export interface VEOProject {
  id: number
  project_name: string
  created_at: string
  updated_at: string
  shot_count: number
  status: 'active' | 'archived' | 'completed'
}

export interface VEOProjectResponse {
  success: boolean
  project?: VEOProject
  projects?: VEOProject[]
  error?: string
}
