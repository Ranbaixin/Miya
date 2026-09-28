/** Parse stored emotion scores without executing content from memory files. */
export function parseEmotions(value: unknown): Record<string, number> | null {
  let parsed: unknown = value
  if (typeof parsed === 'string') {
    try {
      parsed = JSON.parse(parsed)
    }
    catch {
      return null
    }
  }

  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed))
    return null

  const entries = Object.entries(parsed)
  if (!entries.every(([, score]) => typeof score === 'number' && Number.isFinite(score)))
    return null

  return Object.fromEntries(entries) as Record<string, number>
}
