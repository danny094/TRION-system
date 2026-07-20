import { ApiError } from '@/lib/api/client'
import type {
  EffectiveModelSettingsResponse,
  ModelCatalogEntry,
  ModelRole,
  ProviderId,
} from '@/features/settings/api'

export interface RoleConfig {
  role: ModelRole
  label: string
  description: string
}

export interface RoleState {
  provider: string
  model: string
  sourceProvider: string
  sourceModel: string
  providerSourceKind: string
  modelSourceKind: string
}

export const ROLE_CONFIGS: RoleConfig[] = [
  {
    role: 'THINKING',
    label: 'Thinking',
    description: 'Planung, Analyse und tiefe Ableitung.',
  },
  {
    role: 'CONTROL',
    label: 'Control',
    description: 'Verifier, Sicherheits- und Policy-Entscheidungen.',
  },
  {
    role: 'OUTPUT',
    label: 'Output',
    description: 'Finale Antwort, die in Chat und UI sichtbar wird.',
  },
]

export const SOURCE_LABELS: Record<string, string> = {
  override: 'Override',
  env: 'Env',
  default: 'Default',
}

export function buildRoleState(
  payload: EffectiveModelSettingsResponse
): Record<ModelRole, RoleState> {
  return {
    THINKING: roleFromEffective(payload, 'THINKING'),
    CONTROL: roleFromEffective(payload, 'CONTROL'),
    OUTPUT: roleFromEffective(payload, 'OUTPUT'),
  }
}

function roleFromEffective(
  payload: EffectiveModelSettingsResponse,
  role: ModelRole
): RoleState {
  const providerKey = `${role}_PROVIDER`
  const modelKey = `${role}_MODEL`
  const providerValue = payload.effective[providerKey]
  const modelValue = payload.effective[modelKey]

  return {
    provider: providerValue?.value ?? '',
    model: modelValue?.value ?? '',
    sourceProvider: providerValue?.value ?? '',
    sourceModel: modelValue?.value ?? '',
    providerSourceKind: providerValue?.source ?? '',
    modelSourceKind: modelValue?.source ?? '',
  }
}

export function dedupeModelNames(models: ModelCatalogEntry[]): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const entry of models) {
    const key = entry.name.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    out.push(entry.name)
  }
  return out
}

export function visibleModelsForProvider(
  provider: ProviderId,
  models: ModelCatalogEntry[],
  showAllOpenRouter: boolean,
  activeModel: string
): ModelCatalogEntry[] {
  if (provider !== 'openrouter' || showAllOpenRouter) {
    return models
  }
  const recommended = models.filter((entry) => entry.category === 'recommended')
  if (!activeModel) {
    return recommended.length > 0 ? recommended : models
  }
  const active = models.find((entry) => entry.name === activeModel)
  if (!active) {
    return recommended.length > 0 ? recommended : models
  }
  const combined = [...recommended]
  if (!combined.some((entry) => entry.name === active.name)) {
    combined.unshift(active)
  }
  return combined
}

export function roleLabel(role: ModelRole): string {
  return ROLE_CONFIGS.find((item) => item.role === role)?.label ?? role
}

export function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    const detail = typeof error.body?.detail === 'string' ? error.body.detail : ''
    return detail ? `${fallback} ${detail}` : fallback
  }
  if (error instanceof Error && error.message) {
    return `${fallback} ${error.message}`
  }
  return fallback
}
