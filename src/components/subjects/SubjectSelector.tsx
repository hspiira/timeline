import { useEffect, useState } from 'react'
import { SingleSelectCombobox } from '@/components/ui/combobox'
import { timelineApi } from '@/lib/api-client'
import type { SubjectResponse } from '@/lib/types'

type Props = {
  value?: string
  onChange: (v: string) => void
  /** Exclude this subject id from the list. */
  excludeSubjectId?: string | null
  /** Exclude these subject ids from the list (e.g. already linked to a flow). */
  excludeSubjectIds?: string[]
  placeholder?: string
}

export default function SubjectSelector({
  value = '',
  onChange,
  placeholder = 'Select subject',
  excludeSubjectId,
  excludeSubjectIds,
}: Props) {
  const [subjects, setSubjects] = useState<SubjectResponse[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await timelineApi.subjects.list()
        if (!mounted) return
        if (res.data) {
          setSubjects(res.data)
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to load subjects')
        }
      } finally {
        if (mounted) setLoading(false)
      }
    }
    load()
    return () => {
      mounted = false
    }
  }, [])

  const toExclude = excludeSubjectIds ?? (excludeSubjectId ? [excludeSubjectId] : [])
  const filtered =
    toExclude.length > 0 ? subjects.filter((s) => s.id && !toExclude.includes(s.id)) : subjects
  const options = [
    { value: '', label: 'Select subject' },
    ...filtered.map((s) => ({
      value: s.id,
      label: `${s.subject_type} - ${s.external_ref || s.id?.slice(0, 8)}`,
    })),
  ]

  return (
    <div>
      {error && <p className="text-sm text-destructive mb-2">{error}</p>}
      <SingleSelectCombobox
        value={value}
        onValueChange={onChange}
        options={options}
        placeholder={placeholder}
        disabled={loading}
        className="w-full"
      />
    </div>
  )
}
