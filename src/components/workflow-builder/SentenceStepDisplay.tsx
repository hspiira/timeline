/**
 * Renders a human-language step sentence with variables shown as chips (tag-like).
 * Use with sentenceTemplate + sentenceVariables from node config for an
 * agent-style step display (e.g. "Searching for resources by name: [Checkout]").
 */

import {
  getSentenceSegments,
  type SentenceStepConfig,
  substituteSentence,
} from '@/lib/workflow-builder/sentence-templates'

export interface SentenceStepDisplayProps {
  /** Sentence template with {{variable}} placeholders. */
  template: string
  /** Variable values (optional – missing vars show as placeholder). */
  variables?: Record<string, string | number | boolean>
  /** Show variables as chips (tag-like) when true; otherwise plain substituted text. */
  showChips?: boolean
  className?: string
}

/**
 * Renders the sentence with variable segments as inline chips.
 */
export function SentenceStepDisplay({
  template,
  variables = {},
  showChips = true,
  className = '',
}: SentenceStepDisplayProps) {
  if (!template.trim()) return null

  if (!showChips) {
    return (
      <span className={className}>
        {substituteSentence(template, variables, { fallbackMissing: '…' })}
      </span>
    )
  }

  const segments = getSentenceSegments(template, variables)

  return (
    <span className={`inline-flex flex-wrap items-baseline gap-x-1 gap-y-0.5 ${className}`}>
      {segments.map((seg, i) =>
        seg.type === 'text' ? (
          <span key={i}>{seg.value}</span>
        ) : (
          <span
            key={i}
            className="inline-flex rounded-md border border-border bg-muted/60 px-1.5 py-0.5 text-[11px] font-medium text-foreground/90"
          >
            {seg.displayValue ?? `{{${seg.value}}}`}
          </span>
        ),
      )}
    </span>
  )
}

/**
 * Convenience: render from node config that may include sentenceTemplate + sentenceVariables.
 */
export function SentenceStepFromConfig({
  config,
  showChips = true,
  className,
}: {
  config: Record<string, unknown>
  showChips?: boolean
  className?: string
}) {
  const template = (config.sentenceTemplate as string) ?? (config.description as string) ?? ''
  const variables = (config.sentenceVariables as Record<string, string | number | boolean>) ?? {}
  if (!template) return null
  return (
    <SentenceStepDisplay
      template={template}
      variables={variables}
      showChips={showChips}
      className={className}
    />
  )
}
