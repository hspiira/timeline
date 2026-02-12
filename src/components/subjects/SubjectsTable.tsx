import {
    flexRender,
    getCoreRowModel,
    useReactTable,
  } from '@tanstack/react-table'
  import type { ColumnDef } from '@tanstack/react-table'
  import type { SubjectWithMetadata } from '@/hooks/useSubjects'
  import {
      Users,
      Tag,
      ShoppingCart,
      FolderKanban,
      FileText,
      Package,
      Building2,
      User,
      type LucideIcon,
      SquarePen,
    } from 'lucide-react'
  import { useNavigate } from '@tanstack/react-router'
  
  
  // Helper to get icon and color for subject type
  function getSubjectIcon(
      subjectType: string
    ): { icon: LucideIcon; bgColor: string; textColor: string; borderColor: string; accent: string } {
      const type = subjectType.toLowerCase()

      // Map subject types to icons and colors
      const iconMap: Record<string, { icon: LucideIcon; bgColor: string; textColor: string; borderColor: string; accent: string }> = {
        user: { icon: User, bgColor: 'bg-blue-100 dark:bg-blue-900/20', textColor: 'text-blue-600 dark:text-blue-400', borderColor: 'border-blue-200 dark:border-blue-800', accent: 'text-blue-700 dark:text-blue-300' },
        users: { icon: Users, bgColor: 'bg-blue-100 dark:bg-blue-900/20', textColor: 'text-blue-600 dark:text-blue-400', borderColor: 'border-blue-200 dark:border-blue-800', accent: 'text-blue-700 dark:text-blue-300' },
        customer: { icon: Building2, bgColor: 'bg-purple-100 dark:bg-purple-900/20', textColor: 'text-purple-600 dark:text-purple-400', borderColor: 'border-purple-200 dark:border-purple-800', accent: 'text-purple-700 dark:text-purple-300' },
        order: { icon: ShoppingCart, bgColor: 'bg-green-100 dark:bg-green-900/20', textColor: 'text-green-600 dark:text-green-400', borderColor: 'border-green-200 dark:border-green-800', accent: 'text-green-700 dark:text-green-300' },
        project: { icon: FolderKanban, bgColor: 'bg-orange-100 dark:bg-orange-900/20', textColor: 'text-orange-600 dark:text-orange-400', borderColor: 'border-orange-200 dark:border-orange-800', accent: 'text-orange-700 dark:text-orange-300' },
        invoice: { icon: FileText, bgColor: 'bg-amber-100 dark:bg-amber-900/20', textColor: 'text-amber-600 dark:text-amber-400', borderColor: 'border-amber-200 dark:border-amber-800', accent: 'text-amber-700 dark:text-amber-300' },
        shipment: { icon: Package, bgColor: 'bg-cyan-100 dark:bg-cyan-900/20', textColor: 'text-cyan-600 dark:text-cyan-400', borderColor: 'border-cyan-200 dark:border-cyan-800', accent: 'text-cyan-700 dark:text-cyan-300' },
        package: { icon: Package, bgColor: 'bg-cyan-100 dark:bg-cyan-900/20', textColor: 'text-cyan-600 dark:text-cyan-400', borderColor: 'border-cyan-200 dark:border-cyan-800', accent: 'text-cyan-700 dark:text-cyan-300' },
      }

      // Return specific icon or default
      return iconMap[type] || { icon: Tag, bgColor: 'bg-gray-100 dark:bg-gray-900/20', textColor: 'text-gray-600 dark:text-gray-400', borderColor: 'border-gray-200 dark:border-gray-800', accent: 'text-gray-700 dark:text-gray-300' }
    }
  
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
          const { icon: Icon, bgColor, textColor } = getSubjectIcon(subject.subject_type)
          return (
            <div className="flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-xs ${bgColor} flex items-center justify-center shrink-0`}
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
            const { borderColor, accent, bgColor } = getSubjectIcon(subject.subject_type)
            return (
                <span className={`text-sm font-medium ${accent} px-2.5 py-1.5 rounded-xs border ${borderColor} ${bgColor} inline-block`}>
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
                      ? new Date(subject.lastEventDate).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                        })
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
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-xs transition-colors focus:outline-none focus:ring-2 focus:ring-ring/20"
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
      <div className="bg-card/80 backdrop-blur-sm rounded-xs border border-border overflow-hidden">
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
  