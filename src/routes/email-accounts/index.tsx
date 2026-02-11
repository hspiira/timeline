import { createFileRoute, Link } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { useToast } from '@/hooks/useToast'
import { timelineApi } from '@/lib/api-client'
import { Plus, RefreshCw, Mail, CheckCircle, XCircle, Clock, Wifi, WifiOff } from 'lucide-react'
import { DataTable } from '@/components/ui/DataTable'
import type { EmailAccountResponse } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { LoadingIcon, ErrorIcon } from '@/components/ui/icons'
import {
  useSyncProgress,
  getSyncStageText,
  getSyncStageProgress,
  type SyncProgressEvent,
} from '@/hooks/useSyncProgress'

export const Route = createFileRoute('/email-accounts/')({
  component: EmailAccountsPage,
})

/** Progress bar component for sync status */
function SyncProgressBar({ progress }: { progress: SyncProgressEvent }) {
  const percentage = getSyncStageProgress(progress.stage)
  const stageText = getSyncStageText(progress.stage)
  const isFailed = progress.stage === 'failed'
  const isCompleted = progress.stage === 'completed'

  return (
    <div className="flex flex-col gap-1 min-w-[140px]">
      <div className="flex items-center justify-between text-xs">
        <span className={isFailed ? 'text-red-600 dark:text-red-400' : 'text-muted-foreground'}>
          {stageText}
        </span>
        {!isFailed && !isCompleted && (
          <span className="text-muted-foreground">{percentage}%</span>
        )}
      </div>
      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${
            isFailed
              ? 'bg-red-500'
              : isCompleted
                ? 'bg-green-500'
                : 'bg-blue-500'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {progress.messages_fetched > 0 && (
        <span className="text-xs text-muted-foreground">
          {progress.events_created > 0
            ? `${progress.events_created} events from ${progress.messages_fetched} messages`
            : `${progress.messages_fetched} messages`}
        </span>
      )}
      {progress.error && (
        <span className="text-xs text-red-600 dark:text-red-400 truncate" title={progress.error}>
          {progress.error}
        </span>
      )}
    </div>
  )
}

function EmailAccountsPage() {
  const authState = useRequireAuth()
  const toast = useToast()
  const [accounts, setAccounts] = useState<EmailAccountResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [syncing, setSyncing] = useState<string | null>(null)

  // Real-time sync progress via WebSocket
  const { isConnected: wsConnected, getAccountProgress } = useSyncProgress({
    enabled: !!authState.user,
    onProgress: (event) => {
      // Refresh accounts list when sync completes
      if (event.stage === 'completed') {
        fetchAccounts()
        toast.success('Sync completed', `${event.events_created} events created from ${event.messages_fetched} messages`)
      } else if (event.stage === 'failed') {
        toast.error('Sync failed', event.error || 'Unknown error')
      }
    },
  })

  useEffect(() => {
    if (authState.user) {
      fetchAccounts()
    }
  }, [authState.user])

  const fetchAccounts = async () => {
    setLoading(true)
    setError(null)
    try {
      const { data, error: apiError } = await timelineApi.emailAccounts.list()

      if (apiError) {
        const errorObj = apiError as any
        const errorDetail = errorObj?.detail || errorObj?.message || String(apiError)
        setError(typeof errorDetail === 'string' ? errorDetail : 'Failed to load email accounts')
      } else if (data) {
        setAccounts(data)
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unexpected error loading email accounts'
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const handleSync = async (accountId: string, emailAddress: string) => {
    setSyncing(accountId)
    try {
      const { error: apiError } = await timelineApi.emailAccounts.sync(accountId, true)

      if (apiError) {
        const errorMsg =
          typeof apiError === 'object' && 'message' in apiError
            ? (apiError as any).message
            : 'Failed to sync email account'
        toast.error('Sync failed', errorMsg)
      } else {
        toast.success('Sync started', `Syncing emails for ${emailAddress}`)
        // Refresh the list to get updated sync status
        await fetchAccounts()
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to sync email account'
      toast.error('Error syncing', errorMsg)
    } finally {
      setSyncing(null)
    }
  }

  if (!authState.user) {
    return null
  }

  // Define columns for DataTable
  const columns: ColumnDef<EmailAccountResponse>[] = [
    {
      accessorKey: 'email_address',
      header: 'Email Address',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <Mail className="w-4 h-4 text-muted-foreground" />
          <span className="font-medium text-foreground">{row.original.email_address}</span>
        </div>
      ),
    },
    {
      accessorKey: 'provider_type',
      header: 'Provider',
      cell: ({ row }) => (
        <span className="text-xs px-1.5 py-0.5 bg-secondary text-muted-foreground rounded-xs font-mono capitalize">
          {row.original.provider_type}
        </span>
      ),
    },
    {
      id: 'status',
      header: 'Status',
      cell: ({ row }) => {
        const account = row.original
        const progress = getAccountProgress(account.id)

        // Show real-time sync progress if available
        if (progress && progress.stage !== 'completed' && progress.stage !== 'failed') {
          return <SyncProgressBar progress={progress} />
        }

        // Show recently completed/failed status briefly
        if (progress) {
          return <SyncProgressBar progress={progress} />
        }

        // Default status display
        const isActive = account.is_active
        return isActive ? (
          <div className="flex items-center gap-1 text-green-600 dark:text-green-400">
            <CheckCircle className="w-3 h-3" />
            <span className="text-xs">Active</span>
          </div>
        ) : (
          <div className="flex items-center gap-1 text-red-600 dark:text-red-400">
            <XCircle className="w-3 h-3" />
            <span className="text-xs">Inactive</span>
          </div>
        )
      },
    },
    {
      accessorKey: 'last_sync_at',
      header: 'Last Sync',
      cell: ({ row }) => {
        const lastSync = row.original.last_sync_at
        if (!lastSync) {
          return <span className="text-muted-foreground text-sm">Never</span>
        }
        const date = new Date(lastSync)
        const now = new Date()
        const diffMs = now.getTime() - date.getTime()
        const diffMins = Math.floor(diffMs / 60000)
        const diffHours = Math.floor(diffMs / 3600000)
        const diffDays = Math.floor(diffMs / 86400000)

        let timeAgo = ''
        if (diffMins < 1) {
          timeAgo = 'Just now'
        } else if (diffMins < 60) {
          timeAgo = `${diffMins}m ago`
        } else if (diffHours < 24) {
          timeAgo = `${diffHours}h ago`
        } else {
          timeAgo = `${diffDays}d ago`
        }

        return (
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3 text-muted-foreground" />
            <span className="text-muted-foreground text-sm">{timeAgo}</span>
          </div>
        )
      },
    },
    {
      accessorKey: 'created_at',
      header: 'Connected',
      cell: ({ row }) => (
        <span className="text-muted-foreground text-sm">
          {new Date(row.original.created_at).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
          })}
        </span>
      ),
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => {
        const account = row.original
        const progress = getAccountProgress(account.id)
        const isSyncing =
          syncing === account.id ||
          (progress && progress.stage !== 'completed' && progress.stage !== 'failed')

        return (
          <div className="flex items-center justify-end gap-1">
            <button
              onClick={() => handleSync(account.id, account.email_address)}
              disabled={isSyncing || !account.is_active}
              className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title={!account.is_active ? 'Account inactive' : isSyncing ? 'Sync in progress' : 'Sync now'}
            >
              {isSyncing ? (
                <LoadingIcon />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
            </button>
            <Link
              to="/email-accounts/$accountId"
              params={{ accountId: account.id }}
              className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
              title="View details"
            >
              <Mail className="w-4 h-4" />
            </Link>
          </div>
        )
      },
    },
  ]

  return (
    <>
      {/* Error Alert */}
      {error && (
        <div className="mb-3 p-2.5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xs flex gap-2">
          <ErrorIcon className="text-red-600 dark:text-red-400 mt-0.5" />
          <div className="flex-1">
            <h3 className="font-semibold text-red-900 dark:text-red-200 text-sm">Error</h3>
            <p className="text-sm text-red-800 dark:text-red-300 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-foreground">Email Accounts</h1>
            {wsConnected ? (
              <div className="flex items-center gap-1 text-green-600 dark:text-green-400" title="Real-time updates connected">
                <Wifi className="w-3 h-3" />
              </div>
            ) : (
              <div className="flex items-center gap-1 text-muted-foreground" title="Real-time updates disconnected">
                <WifiOff className="w-3 h-3" />
              </div>
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Connect and manage email accounts for automated event tracking
          </p>
        </div>
        <Link to="/email-accounts/create">
          <Button variant="primary" size="md">
            <Plus className="w-4 h-4" />
            Connect Account
          </Button>
        </Link>
      </div>

      {/* Accounts Table */}
      <DataTable
        data={accounts}
        columns={columns}
        isLoading={loading}
        isEmpty={accounts.length === 0}
        compact={true}
        enablePagination={true}
        pageSize={10}
        emptyState={{
          title: 'No email accounts connected',
          description: 'Connect your first email account to start tracking email events automatically',
          action: (
            <Link to="/email-accounts/create">
              <Button variant="primary" size="md">
                <Plus className="w-4 h-4" />
                Connect Account
              </Button>
            </Link>
          ),
        }}
      />
    </>
  )
}
