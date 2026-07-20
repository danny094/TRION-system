export interface PersonaDraft {
  identity: { name: string; role: string; language: string; userName: string }
  style: { tone: string; verbosity: string; format: string; code: string; responseLength: string }
  greetings: { newUser: string; knownUser: string; farewell: string }
  lists: Record<PersonaListKey, string[]>
}

export type PersonaListKey =
  | 'corePhilosophy'
  | 'onboarding'
  | 'adaptation'
  | 'personality'
  | 'capabilities'
  | 'toolAwareness'
  | 'rules'
  | 'privacy'

const SECTION_MAP: Record<string, keyof PersonaDraft['lists'] | 'identity' | 'style' | 'greetings'> = {
  IDENTITY: 'identity',
  CORE_PHILOSOPHY: 'corePhilosophy',
  ONBOARDING: 'onboarding',
  ADAPTATION: 'adaptation',
  PERSONALITY: 'personality',
  STYLE: 'style',
  CAPABILITIES: 'capabilities',
  TOOL_AWARENESS: 'toolAwareness',
  RULES: 'rules',
  PRIVACY: 'privacy',
  GREETINGS: 'greetings',
}

export function createEmptyPersonaDraft(): PersonaDraft {
  return {
    identity: { name: '', role: '', language: '', userName: '' },
    style: { tone: '', verbosity: '', format: '', code: '', responseLength: '' },
    greetings: { newUser: '', knownUser: '', farewell: '' },
    lists: {
      corePhilosophy: [],
      onboarding: [],
      adaptation: [],
      personality: [],
      capabilities: [],
      toolAwareness: [],
      rules: [],
      privacy: [],
    },
  }
}

export function parsePersonaContent(content: string): PersonaDraft {
  const draft = createEmptyPersonaDraft()
  let section = ''

  for (const rawLine of content.split('\n')) {
    const line = rawLine.trim()
    if (!line || line.startsWith('#')) continue
    if (line.startsWith('[') && line.endsWith(']')) {
      section = line.slice(1, -1).toUpperCase()
      continue
    }

    const target = SECTION_MAP[section]
    if (!target) continue
    if (target === 'identity') assignIdentity(draft, line)
    else if (target === 'style') assignStyle(draft, line)
    else if (target === 'greetings') assignGreetings(draft, line)
    else if (line.startsWith('-')) draft.lists[target].push(line.slice(1).trim())
    else if (target === 'rules') draft.lists.rules.push(line.replace(/^\d+\.\s*/, '').trim())
  }

  return draft
}

export function buildPersonaContent(draft: PersonaDraft): string {
  const lines = [
    '[IDENTITY]',
    kv('name', draft.identity.name),
    kv('role', draft.identity.role),
    kv('language', draft.identity.language),
    kv('user_name', draft.identity.userName),
    '',
    block('CORE_PHILOSOPHY', draft.lists.corePhilosophy),
    block('ONBOARDING', draft.lists.onboarding),
    block('ADAPTATION', draft.lists.adaptation),
    block('PERSONALITY', draft.lists.personality),
    '[STYLE]',
    kv('tone', draft.style.tone),
    kv('verbosity', draft.style.verbosity),
    kv('format', draft.style.format),
    kv('code', draft.style.code),
    kv('response_length', draft.style.responseLength),
    '',
    block('CAPABILITIES', draft.lists.capabilities),
    block('TOOL_AWARENESS', draft.lists.toolAwareness),
    ruleBlock(draft.lists.rules),
    block('PRIVACY', draft.lists.privacy),
    '[GREETINGS]',
    kv('greeting_new', draft.greetings.newUser),
    kv('greeting_known', draft.greetings.knownUser),
    kv('farewell', draft.greetings.farewell),
  ]
  return lines.filter((line, index, arr) => !(line === '' && arr[index - 1] === '')).join('\n').trim() + '\n'
}

export function listToText(items: string[]): string {
  return items.join('\n')
}

export function textToList(text: string): string[] {
  return text
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

function assignIdentity(draft: PersonaDraft, line: string) {
  const [key, value] = splitKeyValue(line)
  if (key === 'name') draft.identity.name = value
  else if (key === 'role') draft.identity.role = value
  else if (key === 'language') draft.identity.language = value
  else if (key === 'user_name') draft.identity.userName = value
}

function assignStyle(draft: PersonaDraft, line: string) {
  const [key, value] = splitKeyValue(line)
  if (key === 'tone') draft.style.tone = value
  else if (key === 'verbosity') draft.style.verbosity = value
  else if (key === 'format') draft.style.format = value
  else if (key === 'code') draft.style.code = value
  else if (key === 'response_length') draft.style.responseLength = value
}

function assignGreetings(draft: PersonaDraft, line: string) {
  const [key, value] = splitKeyValue(line)
  if (key === 'greeting_new' || key === 'greeting') draft.greetings.newUser = value
  else if (key === 'greeting_known') draft.greetings.knownUser = value
  else if (key === 'farewell') draft.greetings.farewell = value
}

function splitKeyValue(line: string): [string, string] {
  const [left, ...rest] = line.split(':')
  return [left.trim().toLowerCase(), rest.join(':').trim()]
}

function kv(key: string, value: string): string {
  return `${key}: ${value.trim()}`
}

function block(title: string, items: string[]): string {
  return [`[${title}]`, ...items.map((item) => `- ${item}`), ''].join('\n')
}

function ruleBlock(items: string[]): string {
  return ['[RULES]', ...items.map((item, index) => `${index + 1}. ${item}`), ''].join('\n')
}
