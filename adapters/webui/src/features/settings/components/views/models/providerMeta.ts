import type { ProviderId } from '@/features/settings/api'

import ollamaIcon     from '@/assets/icons/provider/ollama.svg'
import openrouterIcon from '@/assets/icons/provider/openrouter.svg'
import openaiIcon     from '@/assets/icons/provider/openai.svg'
import claudeIcon     from '@/assets/icons/provider/claude-color.svg'
import minimaxIcon    from '@/assets/icons/provider/minimax-color.svg'

export interface ProviderMeta {
  id: ProviderId | string
  label: string
  description: string
  iconUrl: string
}

export const PROVIDER_META: ProviderMeta[] = [
  { id: 'ollama',       label: 'Ollama',       description: 'Lokal gehostete Open-Source-Modelle',        iconUrl: ollamaIcon      },
  { id: 'openrouter',   label: 'OpenRouter',   description: 'Cloud-Zugriff auf hunderte LLMs',             iconUrl: openrouterIcon  },
  { id: 'deepseek',     label: 'DeepSeek',     description: 'Hocheffiziente chinesische KI-Schnittstelle', iconUrl: openaiIcon      },
  { id: 'openai',       label: 'OpenAI',       description: 'GPT-4o und Standardmodelle',                 iconUrl: openaiIcon      },
  { id: 'anthropic',    label: 'Anthropic',    description: 'Claude Modelle',                              iconUrl: claudeIcon      },
  { id: 'minimax',      label: 'MiniMax',      description: 'MiniMax Sprachmodelle',                       iconUrl: minimaxIcon     },
  { id: 'ollama_cloud', label: 'Ollama Cloud', description: 'Cloud-gehostete Ollama-Instanz',              iconUrl: ollamaIcon      },
]

export function getProviderMeta(id: string): ProviderMeta {
  return PROVIDER_META.find((p) => p.id === id) ?? {
    id,
    label: id,
    description: '',
    iconUrl: '',
  }
}
