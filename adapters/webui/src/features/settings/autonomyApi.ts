import { fetchApi } from '@/lib/api/client'

export type AutonomyMode = 'manuell' | 'halbautomatisch' | 'autonom'
export type PlanningDepth = 'schnell' | 'normal' | 'gründlich' | 'unbegrenzt'
export type WaitBehavior = 'sofort' | '30sek' | '2min' | 'immer'
export type SafetyLevel = 'standard' | 'erhöht'
export type ErrorBehavior = 'retry' | 'ask' | 'abort'
export type LoopSensitivity = 2 | 3 | 5 | 10

export interface AutonomyProfile {
  mode: AutonomyMode
  planning_depth: PlanningDepth
  wait_behavior: WaitBehavior
  safety_level: SafetyLevel
  error_behavior: ErrorBehavior
  loop_detection_enabled: boolean
  loop_detection_sensitivity: LoopSensitivity
}

export interface AutonomyProfileResponse {
  profile: AutonomyProfile
  mapped_runtime: Record<string, unknown>
  sources: Record<string, string>
  defaults: AutonomyProfile
  restart_required: boolean
}

export type AutonomyProfileUpdate = Partial<AutonomyProfile>

export interface AutonomyProfileSaveResponse {
  success: boolean
  saved: AutonomyProfileUpdate
  profile: AutonomyProfile
  mapped_runtime: Record<string, unknown>
}

export function fetchAutonomyProfile(): Promise<AutonomyProfileResponse> {
  return fetchApi<AutonomyProfileResponse>('/settings/autonomy/profile')
}

export function updateAutonomyProfile(
  payload: AutonomyProfileUpdate
): Promise<AutonomyProfileSaveResponse> {
  return fetchApi<AutonomyProfileSaveResponse>('/settings/autonomy/profile', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
