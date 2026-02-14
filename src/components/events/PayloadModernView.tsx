/**
 * Renders event payload in a JSON-like structure without quotes on keys or values.
 * Nested objects and arrays are rendered recursively in the same style.
 */

type PayloadValue = string | number | boolean | null | undefined | PayloadValue[] | Record<string, unknown>

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

function PayloadValueDisplay({ value, depth = 0 }: { value: PayloadValue; depth?: number }) {
  if (value === null) {
    return <span className="text-muted-foreground italic">null</span>
  }
  if (value === undefined) {
    return <span className="text-muted-foreground italic">undefined</span>
  }
  if (typeof value === 'boolean') {
    return (
      <span
        className={
          value
            ? 'text-emerald-600 dark:text-emerald-400'
            : 'text-red-600 dark:text-red-400'
        }
      >
        {value ? 'true' : 'false'}
      </span>
    )
  }
  if (typeof value === 'number') {
    return <span className="text-blue-600 dark:text-blue-400">{value}</span>
  }
  if (Array.isArray(value)) {
    const hasComplexItems = value.some(
      (item) => typeof item === 'object' && item !== null
    )
    if (value.length === 0) return <span className="text-muted-foreground">[]</span>
    if (!hasComplexItems) {
      return (
        <span>
          [
          {value.map((item, i) => (
            <span key={i}>
              <PayloadValueDisplay value={item as PayloadValue} depth={depth + 1} />
              {i < value.length - 1 ? ', ' : ''}
            </span>
          ))}
          ]
        </span>
      )
    }
    const indentCh = (depth + 2) * 2 // JSON style: 2 spaces per level
    return (
      <span className="block">
        <span className="text-muted-foreground">[</span>
        <div className="space-y-1" style={{ paddingLeft: `${indentCh}ch` }}>
          {value.map((item, i) => (
            <div key={i}>
              <PayloadValueDisplay value={item as PayloadValue} depth={depth + 1} />
              {i < value.length - 1 ? ',' : ''}
            </div>
          ))}
        </div>
        <span className="text-muted-foreground">]</span>
      </span>
    )
  }
  if (isPlainObject(value)) {
    const entries = Object.entries(value)
    if (entries.length === 0) return <span className="text-muted-foreground">{'{}'}</span>
    const indentCh = (depth + 2) * 2 // JSON style: 2 spaces per level
    return (
      <span className="block">
        <span className="text-muted-foreground">{'{'}</span>
        <div className="space-y-1" style={{ paddingLeft: `${indentCh}ch` }}>
          {entries.map(([k, v]) => (
            <div key={k}>
              <span className="font-medium text-slate-600 dark:text-slate-400">
                {k}:
              </span>{' '}
              <PayloadValueDisplay value={v as PayloadValue} depth={depth + 1} />
            </div>
          ))}
        </div>
        <span className="text-muted-foreground">{'}'}</span>
      </span>
    )
  }
  return <span className="text-foreground">{String(value)}</span>
}

export interface PayloadModernViewProps {
  payload: Record<string, unknown>
  className?: string
}

export function PayloadModernView({ payload, className }: PayloadModernViewProps) {
  const entries = Object.entries(payload)
  if (entries.length === 0) {
    return (
      <p className={`text-xs text-muted-foreground italic ${className ?? ''}`}>
        No data
      </p>
    )
  }
  return (
    <div
      className={`font-mono text-xs text-foreground space-y-1 ${className ?? ''}`}
      style={{ paddingLeft: '2ch' }}
    >
      {entries.map(([key, value]) => (
        <div key={key} className="flex gap-2 flex-wrap items-baseline">
          <span className="font-medium text-slate-600 dark:text-slate-400 shrink-0">
            {key}:
          </span>
          <PayloadValueDisplay value={value as PayloadValue} depth={0} />
        </div>
      ))}
    </div>
  )
}
