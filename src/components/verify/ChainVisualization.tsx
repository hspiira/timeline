import { CheckCircle, AlertTriangle, Link2, Copy, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import type { components } from '@/lib/timeline-api'

type EventResponse = components['schemas']['EventResponse']

interface EventWithVerification extends EventResponse {
  verified: boolean
  expected_hash: string
  actual_hash: string
  previous_hash: string | null
}

interface ChainVisualizationProps {
  events: EventWithVerification[]
  tamperedIndices: number[]
}

export function ChainVisualization({ events, tamperedIndices }: ChainVisualizationProps) {
  const [expandedHashes, setExpandedHashes] = useState<Set<string>>(new Set())
  const [copiedHash, setCopiedHash] = useState<string | null>(null)

  const isTampered = (index: number) => tamperedIndices.includes(index)
  const isGenesis = (index: number) => index === 0
  const isHashExpanded = (key: string) => expandedHashes.has(key)

  const toggleHashExpanded = (key: string) => {
    setExpandedHashes((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(key)) {
        newSet.delete(key)
      } else {
        newSet.add(key)
      }
      return newSet
    })
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedHash(text)
    setTimeout(() => setCopiedHash(null), 2000)
  }

  const truncateHash = (hash: string, length: number = 32) => hash.slice(0, length)

  const HashDisplay = ({ label, hash, hashKey, isError = false, isMissing = false }: {
    label: string
    hash: string | null
    hashKey: string
    isError?: boolean
    isMissing?: boolean
  }) => {
    if (!hash && !isMissing) return null

    if (!hash && isMissing) {
      return (
        <div className="flex items-center gap-2">
          <span className="font-medium text-xs shrink-0 text-red-700 dark:text-red-300">{label}:</span>
          <div className="text-xs px-2 py-1 rounded-none bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 italic">
            [Missing - Event Tampered]
          </div>
        </div>
      )
    }

    const isExpanded = isHashExpanded(hashKey)
    const displayHash = isExpanded ? hash : truncateHash(hash!)
    const isCopied = copiedHash === hash

    return (
      <div className="flex items-center gap-2 group/hash">
        <span className={`font-medium text-xs shrink-0 ${isError ? 'text-red-700 dark:text-red-300' : 'text-muted-foreground'}`}>
          {label}:
        </span>
        <code
          className={`text-xs font-mono break-all flex-1 px-2 py-1 rounded-none cursor-pointer transition-colors ${
            isError
              ? 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30'
              : 'bg-muted/50 text-muted-foreground hover:bg-muted'
          }`}
          onClick={() => toggleHashExpanded(hashKey)}
          title={hash!}
        >
          {displayHash}
          {hash!.length > 32 && !isExpanded && <span className="text-muted-foreground/60">…</span>}
        </code>
        <div className="flex items-center gap-0.5 opacity-0 group-hover/hash:opacity-100 transition-opacity shrink-0">
          <button
            onClick={() => copyToClipboard(hash!)}
            className="p-1 hover:bg-muted rounded-none transition-colors"
            title="Copy"
            aria-label="Copy hash"
          >
            {isCopied ? (
              <span className="text-xs font-bold text-green-600">✓</span>
            ) : (
              <Copy className="w-3 h-3 text-muted-foreground" />
            )}
          </button>
          {hash!.length > 32 && (
            <button
              onClick={() => toggleHashExpanded(hashKey)}
              className="p-1 hover:bg-muted rounded-none transition-colors"
              title={isExpanded ? 'Collapse' : 'Expand'}
              aria-label={isExpanded ? 'Collapse' : 'Expand'}
            >
              {isExpanded ? (
                <ChevronUp className="w-3 h-3 text-muted-foreground" />
              ) : (
                <ChevronDown className="w-3 h-3 text-muted-foreground" />
              )}
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {events.map((event, index) => {
        const tampered = isTampered(index)
        const genesis = isGenesis(index)

        return (
          <div key={event.id}>
            {/* Event Node */}
            <div
              className={`relative border rounded-none transition-colors ${
                tampered
                  ? 'bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-800 ring-1 ring-red-200/50'
                  : 'bg-background border-border hover:bg-muted/30'
              }`}
            >
              {/* Header Row */}
              <div className="flex items-center gap-3 p-3 border-b border-border/50">
                {/* Status Icon */}
                <div className="shrink-0">
                  {genesis ? (
                    <div className="w-8 h-8 rounded-none bg-primary/20 border-2 border-primary flex items-center justify-center">
                      <span className="text-xs font-bold text-primary">G</span>
                    </div>
                  ) : tampered ? (
                    <div className="relative">
                      <div className="absolute inset-0 bg-red-600 rounded-none blur opacity-25 animate-pulse" />
                      <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400 relative" />
                    </div>
                  ) : (
                    <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />
                  )}
                </div>

                {/* Index and Event Type */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-2 flex-wrap">
                    <span className="text-xs font-semibold text-muted-foreground">#{index.toString().padStart(3, '0')}</span>
                    <h3 className="font-semibold text-foreground text-sm">{event.event_type}</h3>
                  </div>
                </div>

                {/* Status Badges */}
                <div className="flex items-center gap-1 shrink-0">
                  {genesis && (
                    <span className="px-2 py-1 text-xs font-medium bg-primary/20 text-primary rounded-none">
                      Genesis
                    </span>
                  )}
                  {tampered && (
                    <span className="px-2 py-1 text-xs font-semibold bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 rounded-none">
                      Failed
                    </span>
                  )}
                </div>
              </div>

              {/* Details Section */}
              <div className="px-3 py-2.5 space-y-2">
                {/* Time Row */}
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-medium text-muted-foreground shrink-0">Time:</span>
                  <span className="text-muted-foreground">{new Date(event.event_time).toLocaleString()}</span>
                </div>

                {/* Event ID Row */}
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-medium text-muted-foreground shrink-0">Event ID:</span>
                  <code className="font-mono text-muted-foreground flex-1 break-all">{event.id.slice(0, 20)}…</code>
                </div>

                {/* Hash Information */}
                {(event.previous_hash || event.expected_hash || event.actual_hash) && (
                  <div className="space-y-2 mt-3 pt-2.5 border-t border-border/50">
                    {!genesis && event.previous_hash && (
                      <HashDisplay label="Previous Hash" hash={event.previous_hash} hashKey={`${index}-prev`} />
                    )}

                    {event.expected_hash && (
                      <HashDisplay
                        label={tampered ? 'Expected Hash' : 'Hash'}
                        hash={event.expected_hash}
                        hashKey={`${index}-expected`}
                        isError={tampered}
                      />
                    )}

                    {tampered && (
                      <HashDisplay
                        label="Actual Hash"
                        hash={event.actual_hash}
                        hashKey={`${index}-actual`}
                        isError={true}
                        isMissing={!event.actual_hash}
                      />
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Chain Link */}
            {index < events.length - 1 && (
              <div className="flex items-center justify-center py-1">
                <div
                  className={`flex items-center gap-1 text-xs font-medium ${
                    isTampered(index + 1)
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-muted-foreground'
                  }`}
                >
                  <Link2 className="w-3 h-3 transform -rotate-90" />
                  Chain Link
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
