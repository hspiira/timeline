import {
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table'
import type { ColumnDef } from '@tanstack/react-table'
import type { SubjectWithMetadata } from '@/hooks/useSubjects'
import { SquarePen } from 'lucide-react'
import { useNavigate } from '@tanstack/react-router'
import { getSubjectTypeTheme } from '@/lib/subject-type-theme'
import { formatShortDate } from '@/lib/format-date'

interface SubjectsTableProps {
    data: SubjectWithMetadata[]
    onEdit?: (subject: SubjectWithMetadata) => void
  }

  export function SubjectsTable({ data, onEdit }: SubjectsTableProps) {
    const navigate = useNavigate()

    const columns: ColumnDef<SubjectWithMetadata>[] = [
      {
        accessorKey: 'id',
        header: 'Subject',
        cell: ({ row }) => {
          const subject = row.original
          const { icon: Icon, bgColor, textColor } = getSubjectTypeTheme(subject.subject_type)
          return (
            <div className="flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-none ${bgColor} flex items-center justify-center shrink-0`}
              >
                <Icon className={`w-4 h-4 ${textColor}`} />
              </div>
              <div className="min-w-0">
                <p className="font-medium text-foreground truncate text-sm">{subject.id}</p>
                {subject.external_ref && (
                  <p className="text-xs text-muted-foreground truncate">
                    {subject.external_ref}
                  </p>
                )}
              </div>
            </div>
          )
        },
      },
      {
        accessorKey: 'subject_type',
        header: 'Type',
        cell: ({ row }) => {
            const subject = row.original
            const { borderColor, accent, bgColor } = getSubjectTypeTheme(subject.subject_type)
            return (
                <span className={`text-sm font-medium ${accent} px-2.5 py-1.5 rounded-none border ${borderColor} ${bgColor} inline-block`}>
                    {subject.subject_type}
                </span>
            )
        }
      },
      {
        accessorKey: 'eventCount',
        header: 'Events',
        cell: ({ row }) => {
            const subject = row.original
            return (
                <span className="text-sm font-medium text-foreground">{subject.eventCount}</span>
            )
        }
      },
      {
        accessorKey: 'lastEventDate',
        header: 'Last Event',
        cell: ({ row }) => {
            const subject = row.original
            return (
                <span className="text-sm text-muted-foreground">
                    {subject.lastEventDate
                      ? formatShortDate(subject.lastEventDate)
                      : '—'}
                </span>
            )
        }
      },
      {
        accessorKey: 'subject_type',
        id: 'external_ref',
        header: 'External Ref',
        cell: ({ row }) => {
            const subject = row.original
            return (
                <span className="text-sm text-muted-foreground">
                    {subject.external_ref || '—'}
                </span>
            )
        }
      },
      {
        id: 'actions',
        header: 'Actions',
        cell: ({ row }) => {
          const subject = row.original
          return (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onEdit?.(subject)
              }}
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-none transition-colors focus:outline-none focus:ring-2 focus:ring-ring/20"
              title="Edit subject"
              aria-label="Edit subject"
            >
              <SquarePen className="w-4 h-4" />
            </button>
          )
        }
      },
    ]

    const table = useReactTable({
      data,
      columns,
      getCoreRowModel: getCoreRowModel(),
    })
  
    const handleSubjectClick = (subjectId: string) => {
      navigate({ to: `/subjects/${subjectId}` })
    }
  
    return (
      <div className="bg-card/80 backdrop-blur-sm rounded-none border border-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-max">
            <thead className="bg-muted/50 border-b border-border sticky top-0">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-2 sm:px-4 py-2 sm:py-3 text-left text-xs sm:text-sm font-semibold text-foreground whitespace-nowrap"
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="divide-y divide-border">
              {table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => handleSubjectClick(row.original.id)}
                  className="hover:bg-muted/50 transition-colors cursor-pointer focus-within:bg-muted/30"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-2 sm:px-4 py-2 sm:py-3 text-xs sm:text-sm">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }
  