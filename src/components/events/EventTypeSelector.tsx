import { Select } from '@/components/ui/select'
import { useEventTypes } from '@/hooks/useEventTypes'

type Props = {
  value?: string
  onChange: (v: string) => void
  className?: string
}

export default function EventTypeSelector({ value, onChange, className = '' }: Props) {
  const { types, loading, error } = useEventTypes()

  return (
    <div className={`w-full min-w-0 ${className}`}>
      <Select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        error={error || undefined}
        disabled={loading}
        className="min-h-[2.25rem]"
      >
        <option value="">Select event type</option>
        {loading ? (
          <option value="">Loading...</option>
        ) : types.length === 0 ? (
          <option value="">No event types — add schemas in Settings</option>
        ) : (
          types.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))
        )}
      </Select>
    </div>
  )
}
