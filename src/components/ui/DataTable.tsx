import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
} from '@tanstack/react-table'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useState, useMemo, useRef, useEffect } from 'react'
import type { ReactNode } from 'react'
import { Button } from './button'
import { Loader2, ChevronLeft, ChevronRight } from 'lucide-react'

/**
 * DataTable Component - Unified table component for all data display needs
 *
 * @template TData The shape of the data being displayed
 *
 * @example
 * // Basic usage without pagination, standard padding
 * <DataTable
 *   data={roles}
 *   columns={columns}
 *   isLoading={loading}
 *   isEmpty={roles.length === 0}
 *   variant="default"
 * />
 *
 * @example
 * // With pagination enabled, showing 20 items per page
 * <DataTable
 *   data={permissions}
 *   columns={columns}
 *   enablePagination={true}
 *   pageSize={20}
 *   variant="default"
 * />
 *
 * @example
 * // Compact table with reduced padding
 * <DataTable
 *   data={documents}
 *   columns={columns}
 *   rowPadding="py-1 sm:py-2 px-2 sm:px-3"
 *   variant="documents"
 * />
 *
 * @example
 * // Pagination with custom padding
 * <DataTable
 *   data={workflows}
 *   columns={columns}
 *   enablePagination={true}
 *   pageSize={15}
 *   rowPadding="py-1.5 sm:py-2.5 px-2 sm:px-3"
 * />
 */
export interface DataTableProps<TData> {
  /** Array of data to display in the table */
  data: TData[]
  /** Column definitions for TanStack React Table */
  columns: ColumnDef<TData>[]
  /** Show loading spinner instead of table */
  isLoading?: boolean
  /** Treat as empty even if data exists */
  isEmpty?: boolean
  /** Custom empty state configuration */
  emptyState?: {
    icon?: React.ComponentType<{ className?: string }>
    title?: string
    description?: string
    action?: ReactNode
  }
  /** Color scheme variant: 'default' | 'documents' | 'subjects' */
  variant?: 'default' | 'documents' | 'subjects'
  /** Callback when a row is clicked */
  onRowClick?: (row: TData) => void
  /** Return a stable id for each row (used for selection and scroll-into-view) */
  getRowId?: (row: TData) => string
  /** When set, the row with this id is shown as selected (persistent highlight) */
  selectedRowId?: string | null
  /** Optional extra class for each row (e.g. highlight broken integrity) */
  getRowClassName?: (row: TData) => string
  /** Make header sticky when scrolling */
  sticky?: boolean
  /** Apply responsive text sizing (text-xs sm:text-sm) */
  responsiveText?: boolean
  /** Enable pagination controls at bottom of table */
  enablePagination?: boolean
  /** Initial page size (default: 10). Available options: 5, 10, 20, 50 */
  pageSize?: number
  /** Compact mode: reduces padding and spacing (default: false) */
  compact?: boolean
  /** Custom row padding classes (default: 'py-2 sm:py-3 px-2 sm:px-4').
   *  Examples:
   *  - Compact: 'py-1 sm:py-2 px-2 sm:px-3'
   *  - Spacious: 'py-3 sm:py-4 px-3 sm:px-5'
   *  - Extra compact: 'py-1 px-2'
   */
  rowPadding?: string
  /** When true and data.length > virtualScrollThreshold, render table body with virtual scroll */
  enableVirtualization?: boolean
  /** Minimum rows to enable virtual scroll (default: 50) */
  virtualScrollThreshold?: number
  /** Height of the scrollable body in px or CSS value (default: 400) */
  virtualScrollHeight?: number | string
  /** Estimated row height in px for virtualizer (default: 48) */
  virtualScrollRowHeight?: number
  /** CSS grid-template-columns for virtualized body so cells align with header (default for subjects variant) */
  virtualScrollGridColumns?: string
}

interface ColorScheme {
  header: string
  headerText: string
  border: string
  hoverBg: string
  rowBorder: string
  bgCard: string
}

const colorSchemes: Record<string, ColorScheme> = {
  default: {
    header: 'bg-muted/50',
    headerText: 'text-foreground',
    border: 'border-border',
    hoverBg: 'hover:bg-muted/50',
    rowBorder: 'border-b border-border',
    bgCard: 'bg-card/80 backdrop-blur-sm',
  },
  documents: {
    header: 'bg-muted/50',
    headerText: 'text-foreground',
    border: 'border-border',
    hoverBg: 'hover:bg-muted/50',
    rowBorder: 'border-b border-border',
    bgCard: '',
  },
  subjects: {
    header: 'border-b border-border/60',
    headerText: 'text-muted-foreground font-display font-semibold uppercase tracking-wider text-xs',
    border: 'border-border/60',
    hoverBg: 'hover:bg-muted/50',
    rowBorder: 'border-b border-border/40',
    bgCard: 'bg-card/80 backdrop-blur-sm',
  },
}

const SUBJECTS_VIRTUAL_GRID_COLUMNS = 'minmax(180px,2fr) minmax(80px,1fr) 90px 70px minmax(90px,1fr) minmax(140px,1fr) 44px'

export function DataTable<TData>({
  data,
  columns,
  isLoading = false,
  isEmpty = false,
  emptyState,
  variant = 'default',
  onRowClick,
  getRowId,
  selectedRowId = null,
  getRowClassName,
  sticky = true,
  responsiveText = true,
  enablePagination = false,
  pageSize: initialPageSize = 10,
  compact = false,
  rowPadding,
  enableVirtualization = false,
  virtualScrollThreshold = 50,
  virtualScrollHeight = 400,
  virtualScrollRowHeight = 48,
  virtualScrollGridColumns,
}: DataTableProps<TData>) {
  const [pageIndex, setPageIndex] = useState(0)
  const [pageSize, setPageSize] = useState(initialPageSize)
  const selectedRowRef = useRef<HTMLTableRowElement | null>(null)
  const selectedVirtualRowRef = useRef<HTMLDivElement | null>(null)
  const scrollContainerRef = useRef<HTMLDivElement | null>(null)

  const pageSizeOptions = [5, 10, 20, 50]

  const useVirtual =
    enableVirtualization && data.length > virtualScrollThreshold

  // Apply compact padding if not explicitly specified
  const effectiveRowPadding = rowPadding ?? (compact ? 'py-1 sm:py-2 px-2 sm:px-3' : variant === 'subjects' ? 'py-2 px-4' : 'py-2 sm:py-3 px-2 sm:px-4')
  const effectiveHeaderPadding = variant === 'subjects' ? 'py-2 px-4' : (compact ? 'py-1.5 sm:py-2 px-2 sm:px-3' : 'py-2 sm:py-3 px-2 sm:px-4')

  // When virtualizing, table uses full data; otherwise apply pagination
  const tableData = useMemo(() => {
    if (useVirtual || !enablePagination) return data
    const start = pageIndex * pageSize
    return data.slice(start, start + pageSize)
  }, [data, pageIndex, pageSize, enablePagination, useVirtual])

  const table = useReactTable({
    data: tableData,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  const virtualizer = useVirtualizer({
    count: useVirtual ? data.length : 0,
    getScrollElement: () => scrollContainerRef.current,
    estimateSize: () => virtualScrollRowHeight,
    overscan: 8,
  })

  // Scroll selected row into view when selection changes (table row or virtualized row)
  useEffect(() => {
    const el = selectedRowRef.current ?? selectedVirtualRowRef.current
    if (selectedRowId && el) {
      el.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    }
  }, [selectedRowId])

  const scheme = colorSchemes[variant]

  // Calculate pagination info
  const totalPages = Math.max(1, Math.ceil(data.length / pageSize))
  const hasPreviousPage = pageIndex > 0
  const hasNextPage = pageIndex < totalPages - 1

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex items-center gap-3 text-muted-foreground">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm">Loading...</span>
        </div>
      </div>
    )
  }

  const rows = table.getRowModel().rows
  const hasData = !isEmpty && (useVirtual ? data.length > 0 : rows.length > 0)

  if (!hasData) {
    return (
      emptyState ? (
        <div className={`rounded-none border ${scheme.border} p-6 text-center`}>
          {emptyState.icon && <emptyState.icon className="w-12 h-12 text-muted-foreground/50 mx-auto mb-3" />}
          {emptyState.title && (
            <h3 className="text-sm font-semibold text-foreground mb-2">
              {emptyState.title}
            </h3>
          )}
          {emptyState.description && (
            <p className="text-sm text-muted-foreground mb-4">
              {emptyState.description}
            </p>
          )}
          {emptyState.action && <div>{emptyState.action}</div>}
        </div>
      ) : (
        <div className={`rounded-none border ${scheme.border} p-8 text-center`}>
          <p className="text-sm text-muted-foreground">No data to display</p>
        </div>
      )
    )
  }

  const isSubjectsVariant = variant === 'subjects'
  const selectedRowBg = 'bg-muted/70'

  const gridColumns =
    virtualScrollGridColumns ??
    (variant === 'subjects' ? SUBJECTS_VIRTUAL_GRID_COLUMNS : `repeat(${columns.length}, 1fr)`)

  if (useVirtual) {
    const virtualItems = virtualizer.getVirtualItems()
    const totalSize = virtualizer.getTotalSize()
    const scrollHeight =
      typeof virtualScrollHeight === 'number' ? `${virtualScrollHeight}px` : virtualScrollHeight

    return (
      <div className={`overflow-hidden ${isSubjectsVariant ? 'rounded-none bg-card/80 backdrop-blur-sm' : `rounded-none border ${scheme.border}`}`}>
        <div className="overflow-x-auto">
          <table className={`w-full min-w-max ${isSubjectsVariant ? 'text-sm' : 'text-xs sm:text-sm'}`} style={{ tableLayout: 'fixed' }}>
            <thead className={`${scheme.header} ${!isSubjectsVariant ? `border-b ${scheme.border}` : ''} ${sticky ? 'sticky top-0 z-10 bg-card/95 backdrop-blur-sm' : ''}`}>
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className={`text-left ${effectiveHeaderPadding} ${scheme.headerText} whitespace-nowrap ${!isSubjectsVariant ? 'font-semibold' : ''}`}
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
          </table>
          <div
            ref={scrollContainerRef}
            className="overflow-y-auto overflow-x-auto"
            style={{ height: scrollHeight }}
          >
            <div style={{ height: totalSize, position: 'relative' }}>
              {virtualItems.map((virtualItem) => {
                const row = rows[virtualItem.index]
                if (!row) return null
                const rowId = getRowId?.(row.original)
                const isSelected = selectedRowId != null && rowId != null && selectedRowId === rowId
                return (
                  <div
                    key={virtualItem.key}
                    role="row"
                    ref={isSelected ? selectedVirtualRowRef : undefined}
                    onClick={() => onRowClick?.(row.original)}
                    className={`grid transition-colors ${scheme.hoverBg} ${isSubjectsVariant ? 'border-b border-border/40' : scheme.rowBorder} ${onRowClick ? 'cursor-pointer' : ''} ${isSelected ? selectedRowBg : ''} ${getRowClassName?.(row.original) ?? ''}`}
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      minWidth: 'max-content',
                      transform: `translateY(${virtualItem.start}px)`,
                      gridTemplateColumns: gridColumns,
                    }}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <div
                        key={cell.id}
                        role="gridcell"
                        className={`${effectiveRowPadding} ${responsiveText ? 'text-xs sm:text-sm' : ''} min-w-0 truncate`}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </div>
                    ))}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`overflow-hidden ${isSubjectsVariant ? 'rounded-none bg-card/80 backdrop-blur-sm' : `rounded-none border ${scheme.border}`}`}>
      <div className="overflow-x-auto">
        <table className={`w-full min-w-max ${isSubjectsVariant ? 'text-sm' : 'text-xs sm:text-sm'}`}>
          <thead className={`${scheme.header} ${!isSubjectsVariant ? `border-b ${scheme.border}` : ''} ${sticky ? 'sticky top-0 z-10 bg-card/95 backdrop-blur-sm' : ''}`}>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className={`text-left ${effectiveHeaderPadding} ${scheme.headerText} whitespace-nowrap ${!isSubjectsVariant ? 'font-semibold' : ''}`}
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
          <tbody className={isSubjectsVariant ? '' : 'divide-y divide-border'}>
            {rows.map((row) => {
              const rowId = getRowId?.(row.original)
              const isSelected = selectedRowId != null && rowId != null && selectedRowId === rowId
              return (
                <tr
                  key={row.id}
                  ref={isSelected ? selectedRowRef : undefined}
                  onClick={() => onRowClick?.(row.original)}
                  className={`transition-colors ${!isSubjectsVariant && scheme.rowBorder} ${
                    onRowClick ? `cursor-pointer ${scheme.hoverBg}` : ''
                  } ${isSubjectsVariant ? 'border-b border-border/40 last:border-b-0' : ''} ${onRowClick && responsiveText && !isSubjectsVariant ? 'focus-within:bg-muted/30' : ''} ${isSelected ? selectedRowBg : ''} ${getRowClassName?.(row.original) ?? ''}`}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      className={`${effectiveRowPadding} ${responsiveText ? 'text-xs sm:text-sm' : ''}`}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      {enablePagination && data.length > 0 && (
        <div className={`flex flex-col sm:flex-row items-center justify-between border-t border-border bg-muted/20 ${compact ? 'gap-2 px-3 py-2' : 'gap-3 px-4 py-3'}`}>
          <div className={`flex items-center ${compact ? 'gap-1' : 'gap-2'} ${compact ? 'text-xs' : 'text-sm'} text-muted-foreground`}>
            <span>Show</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value))
                setPageIndex(0)
              }}
              className={`bg-background border border-input rounded-none text-foreground focus:outline-none focus:ring-2 focus:ring-ring ${compact ? 'px-1.5 py-0.5 text-xs' : 'px-2.5 py-1 text-sm'}`}
            >
              {pageSizeOptions.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
            <span>rows per page</span>
          </div>

          <div className={`flex items-center ${compact ? 'gap-1' : 'gap-2'} ${compact ? 'text-xs' : 'text-sm'} text-muted-foreground`}>
            <span>
              {data.length === 0
                ? '0 items'
                : `${pageIndex * pageSize + 1}–${Math.min((pageIndex + 1) * pageSize, data.length)} of ${data.length}`}
            </span>
          </div>

          <div className={`flex items-center ${compact ? 'gap-0.5' : 'gap-1'}`}>
            <Button
              onClick={() => setPageIndex(Math.max(0, pageIndex - 1))}
              disabled={!hasPreviousPage}
              variant="ghost"
              size="sm"
              title="Previous page"
              aria-label="Previous page"
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <span className={`${compact ? 'px-1 text-xs' : 'px-2 text-sm'} text-muted-foreground`}>
              {pageIndex + 1} / {totalPages}
            </span>
            <Button
              onClick={() => setPageIndex(Math.min(totalPages - 1, pageIndex + 1))}
              disabled={!hasNextPage}
              variant="ghost"
              size="sm"
              title="Next page"
              aria-label="Next page"
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

export default DataTable
