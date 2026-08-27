const PROVIDER_KEY_NAMES = [
  {
    provider: 'Ollama Cloud',
    recommended: 'OLLAMA_API_KEY',
    aliases: ['OLLAMA_CLOUD_API_KEY', 'OLLAMA_KEY', 'OLLAMA'],
  },
  {
    provider: 'OpenAI',
    recommended: 'OPENAI_API_KEY',
    aliases: ['OPENAI_KEY'],
  },
  {
    provider: 'Anthropic',
    recommended: 'ANTHROPIC_API_KEY',
    aliases: ['CLAUDE_API_KEY', 'ANTHROPIC_KEY'],
  },
  {
    provider: 'OpenRouter',
    recommended: 'OPENROUTER_API_KEY',
    aliases: ['OPENROUTER_KEY'],
  },
  {
    provider: 'DeepSeek',
    recommended: 'DEEPSEEK_API_KEY',
    aliases: ['DEEPSEEK_KEY', 'DEEPSEEK'],
  },
  {
    provider: 'MiniMax',
    recommended: 'MINIMAX_API_KEY',
    aliases: ['MINIMAX_KEY'],
  },
]

export function ApiKeyNamingHelp() {
  return (
    <section className="rounded-3xl border border-amber-500/20 bg-amber-500/10 p-4">
      <h3 className="text-xs font-semibold uppercase tracking-widest text-amber-200/80">
        Welche Namen der Backend-Resolver liest
      </h3>
      <p className="mt-2 text-sm text-amber-50/75">
        Speichere Keys unter diesen Namen, damit der LLM-Layer sie intern automatisch auflösen kann.
      </p>

      <div className="mt-4 grid gap-3">
        {PROVIDER_KEY_NAMES.map((entry) => (
          <div
            key={entry.provider}
            className="rounded-2xl border border-white/8 bg-black/15 px-4 py-3"
          >
            <div className="text-xs font-medium uppercase tracking-[0.14em] text-white/45">
              {entry.provider}
            </div>
            <div className="mt-2 font-mono text-xs text-white/85">
              Empfohlen: {entry.recommended}
            </div>
            <div className="mt-2 text-xs text-white/45">
              Alternativen: {entry.aliases.join(', ')}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
