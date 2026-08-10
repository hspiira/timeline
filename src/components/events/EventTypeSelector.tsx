import { SingleSelectCombobox, optionsFromStrings } from '@/components/ui/combobox'
import { useEventTypes } from '@/hooks/useEventTypes'

type Props = {
  value?: string
  onChange: (v: string) => void
  className?: string
}

export default function EventTypeSelector({ value = '', onChange, className = '' }: Props) {
  const { types, loading, error } = useEventTypes()

  const options = loading
    ? [{ value: '', label: 'Loading...' }]
    : types.length === 0
      ? [{ value: '', label: 'No event types — add schemas in Settings' }]
      : optionsFromStrings(types, { value: '', label: 'Select event type' })

  return (
    <div className={`w-full min-w-0 ${className}`}>
      <SingleSelectCombobox
        value={value}
        onValueChange={onChange}
        options={options}
        placeholder="Select event type"
        error={error || undefined}
        disabled={loading}
        className="min-h-[2.25rem]"
      />
    </div>
  )
}
