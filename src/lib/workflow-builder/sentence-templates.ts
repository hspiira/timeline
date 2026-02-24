/**
 * Human-language sentence templates for workflow steps.
 * Steps are described as sentences with {{variable}} placeholders; variables can be
 * filled from config or at runtime (e.g. trigger payload, previous step output).
 *
 * Example:
 *   template: "Searching for resources by name: {{resource_name}}"
 *   variables: { resource_name: "Checkout" }
 *   → "Searching for resources by name: Checkout"
 *
 * Conditions can be expressed as sentences too, e.g. "When {{field}} {{operator}} {{value}}".
 */

/** Placeholder pattern: {{variable_name}} (one or more word characters / numbers / underscore) */
const PLACEHOLDER_REGEX = /\{\{(\w+)\}\}/g

export interface SentenceStepConfig {
  /** Human-language sentence with {{variable}} placeholders. */
  sentenceTemplate: string
  /** Values for placeholders (config-time or default). Can be extended at runtime. */
  sentenceVariables?: Record<string, string | number | boolean>
}

/**
 * Extract variable names from a sentence template.
 * e.g. "Searching for {{resource_name}} in {{service}}" → ["resource_name", "service"]
 */
export function parseTemplateVariables(template: string): string[] {
  const names: string[] = []
  let m: RegExpExecArray | null
  PLACEHOLDER_REGEX.lastIndex = 0
  while ((m = PLACEHOLDER_REGEX.exec(template)) !== null) {
    if (!names.includes(m[1])) names.push(m[1])
  }
  return names
}

/**
 * Substitute {{variable}} placeholders with values.
 * Missing variables are replaced with the placeholder text or optional fallback.
 */
export function substituteSentence(
  template: string,
  variables: Record<string, string | number | boolean> = {},
  options?: { fallbackMissing?: string }
): string {
  const fallback = options?.fallbackMissing ?? ''
  return template.replace(PLACEHOLDER_REGEX, (_, name) => {
    const v = variables[name]
    if (v === undefined || v === null) return fallback || `{{${name}}}`
    return String(v)
  })
}

/**
 * Split a sentence into segments: plain text and variable slots.
 * Useful for rendering: [ "Searching for ", { name: "resource_name", value: "Checkout" }, " in ", ... ]
 */
export interface SentenceSegment {
  type: 'text' | 'variable'
  /** For type 'text': the literal string. For type 'variable': the variable name. */
  value: string
  /** For type 'variable': the resolved value to display. */
  displayValue?: string
}

export function getSentenceSegments(
  template: string,
  variables: Record<string, string | number | boolean> = {}
): SentenceSegment[] {
  const segments: SentenceSegment[] = []
  let lastIndex = 0
  let m: RegExpExecArray | null
  PLACEHOLDER_REGEX.lastIndex = 0
  while ((m = PLACEHOLDER_REGEX.exec(template)) !== null) {
    if (m.index > lastIndex) {
      segments.push({ type: 'text', value: template.slice(lastIndex, m.index) })
    }
    const varName = m[1]
    const displayValue = variables[varName] != null ? String(variables[varName]) : undefined
    segments.push({ type: 'variable', value: varName, displayValue })
    lastIndex = m.index + m[0].length
  }
  if (lastIndex < template.length) {
    segments.push({ type: 'text', value: template.slice(lastIndex) })
  }
  return segments
}

/** Default sentence templates per node type (for prompts or defaults). */
export const DEFAULT_SENTENCE_TEMPLATES: Record<string, string> = {
  trigger: 'When an event of type {{event_type}} is created',
  condition: 'When {{field}} {{operator}} {{value}}',
  action: '{{action_type}}: {{description}}',
}
