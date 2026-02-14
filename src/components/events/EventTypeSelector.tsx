import { useEffect, useState } from 'react'
import { timelineApi } from '@/lib/api-client'
import { getApiErrorMessage } from '@/lib/api-utils'
import { Select } from '@/components/ui/select'

type Props = {
  value?: string
  onChange: (v: string) => void
  className?: string
}

function extractTypesFromSchemaList(data: unknown): string[] {
  if (Array.isArray(data)) {
    return [...new Set(data.map((s: { event_type?: string }) => s.event_type).filter(Boolean)) as string[]]
  }
  if (data && typeof data === 'object' && 'items' in data && Array.isArray((data as { items: unknown[] }).items)) {
    const items = (data as { items: { event_type?: string }[] }).items
    return [...new Set(items.map((s) => s.event_type).filter(Boolean)) as string[]]
  }
  return []
}

export default function EventTypeSelector({ value, onChange, className = '' }: Props) {
  const [types, setTypes] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const { data: schemaList, error: schemaError } = await timelineApi.eventSchemas.list({ limit: 500 })
        if (!mounted) return
        const fromSchemas = extractTypesFromSchemaList(schemaList)
        if (fromSchemas.length > 0) {
          setTypes(fromSchemas)
          return
        }
        if (schemaError) {
          setError(getApiErrorMessage(schemaError, 'Failed to load event types'))
        }
        // Fallback: derive from events when schema list is empty or failed
        const { data: eventsList } = await timelineApi.events.listAll()
        if (!mounted) return
        if (eventsList && Array.isArray(eventsList)) {
          const fromEvents = [...new Set(eventsList.map((e: { event_type?: string }) => e.event_type).filter(Boolean))] as string[]
          if (fromEvents.length > 0) {
            setTypes(fromEvents)
            setError(null)
          }
        }
      } catch (err) {
        if (mounted) {
          setError(getApiErrorMessage(err, 'An unexpected error occurred'))
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }
    load()
    return () => { mounted = false }
  }, [])

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
