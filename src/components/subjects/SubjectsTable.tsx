import type { ColumnDef } from '@tanstack/react-table'
import type { SubjectWithMetadata } from '@/hooks/useSubjects'
import { SquarePen } from 'lucide-react'
import { Link } from '@tanstack/react-router'
import { useState, useMemo } from 'react'
import { formatEventDate } from '@/lib/format-date'
import { DataTable } from '@/components/ui/DataTable'
import { getSubjectTypeThemeFromConfig } from '@/lib/subject-type-theme'
import type { components } from '@/lib/timeline-api'

type SubjectTypeListItem = components['schemas']['SubjectTypeListItem']

interface SubjectsTableProps {
  data: SubjectWithMetadata[]
  onEdit?: (subject: SubjectWithMetadata) => void
  /** Subject types from API (Settings → Subject types); used for icon and Type column label */
  subjectTypeConfig?: SubjectTypeListItem[]
}

function getTypeDisplayName(
  subjectType: string,
  config?: SubjectTypeListItem[]
): string {
  const found = config?.find(
    (t) => t.type_name.toLowerCase() === subjectType.toLowerCase()
  )
  return found?.display_name ?? subjectType
}

export function SubjectsTable({
  data,
  onEdit,
  subjectTypeConfig,
}: SubjectsTableProps) {
  const [selectedSubjectId, setSelectedSubjectId] = useState<string | null>(null)

  const columns: ColumnDef<SubjectWithMetadata>[] = useMemo(
    () => [
    {
      accessorKey: 'id',
      header: 'Subject',
      cell: ({ row }) => {
        const subject = row.original
        const theme = getSubjectTypeThemeFromConfig(
          subject.subject_type,
          subjectTypeConfig
        )
        const Icon = theme.icon
        const useConfigColor = theme.configColor != null && theme.configColor !== ''
        return (
          <div className="flex items-center gap-2">
            <div
              className={`w-8 h-8 rounded-none flex items-center justify-center shrink-0 ${useConfigColor ? '' : theme.bgColor}`}
              style={
                useConfigColor && theme.configColor
                  ? {
                      backgroundColor: `${theme.configColor}20`,
                      color: theme.configColor,
                    }
                  : undefined
              }
            >
              <Icon
                className={`w-4 h-4 ${useConfigColor ? '' : theme.textColor}`}
                strokeWidth={1.75}
              />
            </div>
            <Link
              to="/subjects/$subjectId"
              params={{ subjectId: subject.id }}
              search={{ tab: 'events' }}
              onClick={(e) => e.stopPropagation()}
              className="font-medium text-foreground truncate block hover:text-primary transition-colors min-w-0"
              title={subject.display_name ? undefined : subject.id}
            >
              {subject.display_name || subject.id}
            </Link>
          </div>
        )
      },
    },
    {
      accessorKey: 'subject_type',
      header: 'Type',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {getTypeDisplayName(row.original.subject_type, subjectTypeConfig)}
        </span>
      ),
    },
    {
      accessorKey: 'eventCount',
      header: 'Events',
      cell: ({ row }) => (
        <span className="text-sm text-foreground tabular-nums">{row.original.eventCount}</span>
      ),
    },
    {
      accessorKey: 'lastEventDate',
      header: 'Last Event',
      cell: ({ row }) => {
        const d = row.original.lastEventDate
        return (
          <span className="text-sm text-muted-foreground tabular-nums">
            {d ? formatEventDate(d) : '—'}
          </span>
        )
      },
    },
    {
      accessorKey: 'external_ref',
      id: 'external_ref',
      header: 'External Ref',
      cell: ({ row }) => {
        const ref = row.original.external_ref
        return (
          <span className="text-sm text-muted-foreground truncate block max-w-[160px]">
            {ref || '—'}
          </span>
        )
      },
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => {
        const subject = row.original
        return (
          <button
            onClick={(e) => {
              e.stopPropagation()
              onEdit?.(subject)
            }}
            className="p-2 rounded-none text-muted-foreground hover:text-foreground hover:bg-muted transition-colors focus:outline-none focus:ring-2 focus:ring-ring/20"
            title="Edit subject"
            aria-label="Edit subject"
          >
            <SquarePen className="w-4 h-4" strokeWidth={1.75} />
          </button>
        )
      },
    },
  ],
    [subjectTypeConfig, onEdit]
  )

  const handleRowClick = (subject: SubjectWithMetadata) => {
    setSelectedSubjectId((prev) => (prev === subject.id ? null : subject.id))
  }

  return (
    <div className="overflow-hidden">
      <DataTable<SubjectWithMetadata>
        data={data}
        columns={columns}
        onRowClick={handleRowClick}
        getRowId={(row) => row.id}
        selectedRowId={selectedSubjectId}
        variant="subjects"
        enablePagination
        pageSize={20}
        isEmpty={data.length === 0}
      />
    </div>
  )
}
