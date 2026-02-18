import { useEffect, useState } from 'react'
import { timelineApi } from '@/lib/api-client'
import { SubjectResponse } from '@/lib/types'
import { SingleSelectCombobox } from '@/components/ui/combobox'

type Props = {
	value?: string
	onChange: (v: string) => void
	/** Exclude this subject id from the list (e.g. when adding a relationship from subject A, exclude A). */
	excludeSubjectId?: string | null
}

export default function SubjectSelector({ value = '', onChange, excludeSubjectId }: Props) {
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
		return () => { mounted = false }
	}, [])

	const filtered = excludeSubjectId
		? subjects.filter((s) => s.id !== excludeSubjectId)
		: subjects
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
				placeholder="Select subject"
				disabled={loading}
				className="w-full"
			/>
		</div>
	)
}
