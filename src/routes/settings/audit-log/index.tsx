import { createFileRoute } from '@tanstack/react-router'
import { useState, useEffect, useCallback } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { useFetchWithError } from '@/hooks/useFetchWithError'
import { timelineApi } from '@/lib/api-client'
import { ClipboardList, ChevronLeft, ChevronRight, Loader2, AlertCircle } from 'lucide-react'
import { DataTable } from '@/components/ui/DataTable'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import type { components } from '@/lib/timeline-api'

export const Route = createFileRoute('/settings/audit-log/')({
  component: AuditLogPage,
})

type AuditLogEntry = components['schemas']['AuditLogEntryResponse']

const PAGE_SIZE = 20
const RESOURCE_TYPES = [
  '',
  'subject',
  'event',
  'document',
  'user',
  'role',
  'permission',
  'workflow',
  'tenant',
  'audit',
]

function formatTimestamp(ts: string) {
  try {
    const d = new Date(ts)
    return d.toLocaleString(undefined, {
      dateStyle: 'short',
      timeStyle: 'medium',
    })
  } catch {
    return ts
  }
}

function AuditLogPage() {
  const authState = useRequireAuth()
  const [skip, setSkip] = useState(0)
  const [resourceType, setResourceType] = useState<string>('')
  const [userId, setUserId] = useState('')
  const [fromTs, setFromTs] = useState('')
  const [toTs, setToTs] = useState('')

  const fetchAuditLog = useCallback(async () => {
    const res = await timelineApi.auditLog.list({
      skip,
      limit: PAGE_SIZE,
      resource_type: resourceType || undefined,
      user_id: userId.trim() || undefined,
      from_timestamp: fromTs.trim() || undefined,
      to_timestamp: toTs.trim() || undefined,
    })
    if (res.error != null) {
      return { error: res.error, response: res.response }
    }
    const list = res.data
    return {
      data: list
        ? {
            items: list.items ?? [],
            skip: list.skip ?? 0,
            limit: list.limit ?? PAGE_SIZE,
          }
        : { items: [], skip: 0, limit: PAGE_SIZE },
    }
  }, [skip, resourceType, userId, fromTs, toTs])

  const {
    data: fetched,
    error,
    loading,
    hasNoAccess,
    refetch,
  } = useFetchWithError<{
    items: AuditLogEntry[]
    skip: number
    limit: number
  }>(fetchAuditLog, {
    defaultErrorMessage: 'Unable to load audit log',
    enabled: !!authState.user,
  })

  useEffect(() => {
    if (authState.user) refetch()
  }, [authState.user, refetch, skip, resourceType, userId, fromTs, toTs])

  const items = fetched?.items ?? []
  const hasMore = items.length === PAGE_SIZE

  const applyFilters = () => {
    setSkip(0)
  }

  if (!authState.user) {
    return null
  }

  if (hasNoAccess) {
    return (
      <div className="rounded-lg border border-border bg-card p-8 text-center">
        <AlertCircle className="w-12 h-12 text-destructive mx-auto mb-4" />
        <h2 className="text-lg font-semibold text-foreground mb-2">Access denied</h2>
        <p className="text-muted-foreground text-sm max-w-md mx-auto">
          You do not have permission to view the audit log. Contact your administrator if you need access.
        </p>
      </div>
    )
  }

  const columns: ColumnDef<AuditLogEntry>[] = [
    {
      accessorKey: 'timestamp',
      header: 'Time',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground whitespace-nowrap">
          {formatTimestamp(row.original.timestamp)}
        </span>
      ),
    },
    {
      accessorKey: 'user_id',
      header: 'User',
      cell: ({ row }) => (
        <span className="text-sm font-mono">{row.original.user_id ?? '—'}</span>
      ),
    },
    {
      accessorKey: 'action',
      header: 'Action',
      cell: ({ row }) => (
        <span className="text-sm font-medium">{row.original.action}</span>
      ),
    },
    {
      accessorKey: 'resource_type',
      header: 'Resource',
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">{row.original.resource_type}</span>
      ),
    },
    {
      accessorKey: 'resource_id',
      header: 'Resource ID',
      cell: ({ row }) => (
        <span className="text-sm font-mono truncate max-w-[120px] block" title={row.original.resource_id ?? ''}>
          {row.original.resource_id ?? '—'}
        </span>
      ),
    },
    {
      accessorKey: 'success',
      header: 'Success',
      cell: ({ row }) => (
        <span
          className={`text-xs font-medium ${
            row.original.success ? 'text-green-600 dark:text-green-400' : 'text-destructive'
          }`}
        >
          {row.original.success ? 'Yes' : 'No'}
        </span>
      ),
    },
    {
      id: 'details',
      header: 'Details',
      cell: ({ row }) => {
        const entry = row.original
        const hasOld = entry.old_values != null && Object.keys(entry.old_values).length > 0
        const hasNew = entry.new_values != null && Object.keys(entry.new_values).length > 0
        if (!hasOld && !hasNew) return <span className="text-muted-foreground">—</span>
        return (
          <details className="text-xs">
            <summary className="cursor-pointer text-primary hover:underline">
              {[hasOld && 'old', hasNew && 'new'].filter(Boolean).join(' / ')}
            </summary>
            <div className="mt-1 space-y-1 max-w-[240px] overflow-auto">
              {hasOld && (
                <div>
                  <span className="font-medium text-muted-foreground">old:</span>
                  <pre className="mt-0.5 p-1.5 bg-muted/50 rounded border border-border/50 text-[10px] whitespace-pre-wrap break-all">
                    {JSON.stringify(entry.old_values)}
                  </pre>
                </div>
              )}
              {hasNew && (
                <div>
                  <span className="font-medium text-muted-foreground">new:</span>
                  <pre className="mt-0.5 p-1.5 bg-muted/50 rounded border border-border/50 text-[10px] whitespace-pre-wrap break-all">
                    {JSON.stringify(entry.new_values)}
                  </pre>
                </div>
              )}
            </div>
          </details>
        )
      },
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-foreground flex items-center gap-2">
            <ClipboardList className="w-5 h-5" />
            Audit log
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            View tenant audit log entries. Filter by resource type, user, and date range.
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3 p-4 rounded-lg border border-border bg-muted/30">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-muted-foreground">Resource type</label>
          <Select
            value={resourceType || 'all'}
            onChange={(e) => setResourceType(e.target.value === 'all' ? '' : e.target.value)}
            className="w-[140px]"
          >
            <option value="all">All</option>
            {RESOURCE_TYPES.filter(Boolean).map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </Select>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-muted-foreground">User ID</label>
          <Input
            placeholder="User ID"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            className="w-[160px] h-9"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-muted-foreground">From (ISO)</label>
          <Input
            placeholder="YYYY-MM-DDTHH:mm"
            value={fromTs}
            onChange={(e) => setFromTs(e.target.value)}
            className="w-[180px] h-9 font-mono text-sm"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-muted-foreground">To (ISO)</label>
          <Input
            placeholder="YYYY-MM-DDTHH:mm"
            value={toTs}
            onChange={(e) => setToTs(e.target.value)}
            className="w-[180px] h-9 font-mono text-sm"
          />
        </div>
        <Button variant="secondary" size="sm" onClick={applyFilters}>
          Apply filters
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            setResourceType('')
            setUserId('')
            setFromTs('')
            setToTs('')
            setSkip(0)
          }}
        >
          Clear filters
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16 text-muted-foreground">
          <Loader2 className="w-8 h-8 animate-spin mr-2" />
          Loading audit log…
        </div>
      ) : (
        <>
          <DataTable
            data={items}
            columns={columns}
            isLoading={false}
            isEmpty={items.length === 0}
            emptyState={{
              title: 'No audit log entries',
              description: 'No entries match your filters or the log is empty.',
            }}
            variant="default"
            compact
          />

          {/* Server-side pagination */}
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">
              Showing {skip + 1}–{skip + items.length} (page size {PAGE_SIZE})
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSkip((s) => Math.max(0, s - PAGE_SIZE))}
                disabled={skip === 0 || loading}
              >
                <ChevronLeft className="w-4 h-4" />
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSkip((s) => s + PAGE_SIZE)}
                disabled={!hasMore || loading}
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
