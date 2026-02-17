import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { useState, useEffect } from 'react'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { useToast } from '@/hooks/useToast'
import { timelineApi } from '@/lib/api-client'
import {
  ArrowLeft,
  Mail,
  RefreshCw,
  CheckCircle,
  XCircle,
  Server,
  Calendar,
  Clock,
  Trash2,
  AlertTriangle,
  Shield,
  Key,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { LoadingIcon, ErrorIcon } from '@/components/ui/icons'
import { ConfirmModal } from '@/components/ui/ConfirmModal'
import { formatEventDateTime } from '@/lib/format-date'
import type { EmailAccountResponse } from '@/lib/types'

export const Route = createFileRoute('/email-accounts/$accountId')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  component: EmailAccountDetailPage,
})

// Helper to get OAuth status display info
function getOAuthStatusInfo(status: string | null | undefined): {
  label: string
  color: string
  icon: React.ElementType
  description: string
} {
  switch (status) {
    case 'active':
      return {
        label: 'Active',
        color: 'text-green-600 dark:text-green-400',
        icon: CheckCircle,
        description: 'OAuth connection is healthy',
      }
    case 'refresh_failed':
      return {
        label: 'Refresh Failed',
        color: 'text-amber-600 dark:text-amber-400',
        icon: AlertTriangle,
        description: 'Token refresh failed. Re-authentication may be required.',
      }
    case 'consent_denied':
      return {
        label: 'Consent Denied',
        color: 'text-red-600 dark:text-red-400',
        icon: XCircle,
        description: 'User denied access. Re-authentication required.',
      }
    case 'revoked':
      return {
        label: 'Revoked',
        color: 'text-red-600 dark:text-red-400',
        icon: XCircle,
        description: 'Access was revoked. Re-authentication required.',
      }
    case 'expired':
      return {
        label: 'Expired',
        color: 'text-amber-600 dark:text-amber-400',
        icon: Clock,
        description: 'Token has expired. Re-authentication required.',
      }
    default:
      return {
        label: 'Unknown',
        color: 'text-muted-foreground',
        icon: Shield,
        description: 'OAuth status unknown',
      }
  }
}

function EmailAccountDetailPage() {
  const { accountId } = Route.useParams()
  const authState = useRequireAuth()
  const navigate = useNavigate()
  const toast = useToast()

  const [account, setAccount] = useState<EmailAccountResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (authState.user) {
      fetchAccount()
    }
  }, [authState.user, accountId])

  const fetchAccount = async () => {
    setLoading(true)
    setError(null)
    try {
      const { data, error: apiError } = await timelineApi.emailAccounts.get(accountId)

      if (apiError) {
        const errorObj = apiError as any
        const errorDetail = errorObj?.detail || errorObj?.message || String(apiError)
        setError(typeof errorDetail === 'string' ? errorDetail : 'Failed to load email account')
      } else if (data) {
        setAccount(data)
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unexpected error loading email account'
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const handleSync = async () => {
    if (!account) return

    setSyncing(true)
    try {
      const { error: apiError } = await timelineApi.emailAccounts.sync(accountId)

      if (apiError) {
        const errorMsg =
          typeof apiError === 'object' && 'message' in apiError
            ? (apiError as any).message
            : 'Failed to sync email account'
        toast.error('Sync failed', errorMsg)
      } else {
        toast.success('Sync started', `Syncing emails for ${account.email_address}`)
        // Refresh the account to get updated sync status
        await fetchAccount()
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to sync email account'
      toast.error('Error syncing', errorMsg)
    } finally {
      setSyncing(false)
    }
  }

  const handleDelete = async () => {
    if (!account) return

    setDeleting(true)
    try {
      const { error: apiError } = await timelineApi.emailAccounts.delete(accountId)

      if (apiError) {
        const errorMsg =
          typeof apiError === 'object' && 'message' in apiError
            ? (apiError as any).message
            : 'Failed to disconnect email account'
        toast.error('Failed to disconnect', errorMsg)
        throw new Error(errorMsg)
      }

      toast.success('Account disconnected', `${account.email_address} has been disconnected`)
      navigate({ to: '/email-accounts' })
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to disconnect email account'
      toast.error('Error disconnecting', errorMsg)
      throw err
    } finally {
      setDeleting(false)
    }
  }

  if (!authState.user) {
    return null
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingIcon className="w-8 h-8" />
      </div>
    )
  }

  if (error || !account) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-none">
        <ErrorIcon className="w-6 h-6 text-red-600 dark:text-red-400 mb-2" />
        <h3 className="font-semibold text-red-900 dark:text-red-200">Error Loading Account</h3>
        <p className="text-sm text-red-800 dark:text-red-300 mt-1">{error || 'Account not found'}</p>
        <Button onClick={() => navigate({ to: '/email-accounts' })} variant="secondary" size="md" className="mt-3">
          Back to Email Accounts
        </Button>
      </div>
    )
  }

  return (
    <>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate({ to: '/email-accounts' })}
            className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-none transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-lg font-bold text-foreground">Email Account Details</h1>
            <p className="text-sm text-muted-foreground mt-0.5">{account.email_address}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={() => handleSync()}
            disabled={syncing || !account.is_active}
            variant="secondary"
            size="md"
          >
            {syncing ? (
              <>
                <LoadingIcon />
                Syncing...
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                Sync Now
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Account Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
        {/* Status Card */}
        <div className="p-4 bg-card/80 backdrop-blur-sm border border-border/50 rounded-none">
          <div className="flex items-center gap-2 text-muted-foreground mb-2">
            {account.is_active ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
            <span className="text-sm font-medium">Status</span>
          </div>
          <p className="text-lg font-bold text-foreground">
            {account.is_active ? (
              <span className="text-green-600 dark:text-green-400">Active</span>
            ) : (
              <span className="text-red-600 dark:text-red-400">Inactive</span>
            )}
          </p>
        </div>

        {/* Provider Card */}
        <div className="p-4 bg-card/80 backdrop-blur-sm border border-border/50 rounded-none">
          <div className="flex items-center gap-2 text-muted-foreground mb-2">
            <Server className="w-4 h-4" />
            <span className="text-sm font-medium">Provider</span>
          </div>
          <p className="text-lg font-bold text-foreground capitalize">{account.provider_type}</p>
        </div>

        {/* Last Sync Card */}
        <div className="p-4 bg-card/80 backdrop-blur-sm border border-border/50 rounded-none">
          <div className="flex items-center gap-2 text-muted-foreground mb-2">
            <Clock className="w-4 h-4" />
            <span className="text-sm font-medium">Last Sync</span>
          </div>
          <p className="text-lg font-bold text-foreground">
            {account.last_sync_at ? (
              formatEventDateTime(account.last_sync_at)
            ) : (
              <span className="text-muted-foreground">Never</span>
            )}
          </p>
        </div>
      </div>

      {/* Account Details */}
      <div className="bg-card/80 backdrop-blur-sm border border-border/50 rounded-none p-4 mb-6">
        <h2 className="text-base font-semibold text-foreground mb-3">Account Information</h2>
        <div className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground">Email Address</label>
              <div className="flex items-center gap-2 mt-1">
                <Mail className="w-4 h-4 text-muted-foreground" />
                <p className="text-foreground text-sm">{account.email_address}</p>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Provider</label>
              <div className="flex items-center gap-2 mt-1">
                <Server className="w-4 h-4 text-muted-foreground" />
                <p className="text-foreground text-sm capitalize">{account.provider_type}</p>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">Sync Status</label>
              <div className="flex items-center gap-2 mt-1">
                <Calendar className="w-4 h-4 text-muted-foreground" />
                <p className="text-foreground text-sm capitalize">{account.sync_status}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* OAuth Status - Only show for OAuth providers */}
      {(account.provider_type === 'gmail' || account.provider_type === 'outlook') && (
        <div className="bg-card/80 backdrop-blur-sm border border-border/50 rounded-none p-4 mb-6">
          <h2 className="text-base font-semibold text-foreground mb-3">OAuth Status</h2>
          <div className="space-y-4">
            {/* OAuth Status Badge */}
            {(() => {
              const statusInfo = getOAuthStatusInfo(account.oauth_status)
              const StatusIcon = statusInfo.icon
              return (
                <div className="flex items-start gap-3">
                  <div
                    className={`p-2 rounded-none ${
                      account.oauth_status === 'active'
                        ? 'bg-green-100 dark:bg-green-900/30'
                        : account.oauth_status === 'refresh_failed' || account.oauth_status === 'expired'
                          ? 'bg-amber-100 dark:bg-amber-900/30'
                          : 'bg-red-100 dark:bg-red-900/30'
                    }`}
                  >
                    <StatusIcon className={`w-5 h-5 ${statusInfo.color}`} />
                  </div>
                  <div>
                    <p className={`font-semibold ${statusInfo.color}`}>{statusInfo.label}</p>
                    <p className="text-sm text-muted-foreground">{statusInfo.description}</p>
                  </div>
                </div>
              )
            })()}

            {/* Re-authenticate Button for failed states */}
            {account.oauth_status &&
              ['refresh_failed', 'consent_denied', 'revoked', 'expired'].includes(account.oauth_status) && (
                <Button
                  onClick={() => navigate({ to: '/email-accounts/create' })}
                  variant="primary"
                  size="md"
                  className="w-full sm:w-auto"
                >
                  <Key className="w-4 h-4" />
                  Re-authenticate
                </Button>
              )}
          </div>
        </div>
      )}

      {/* Sync Options */}
      <div className="bg-card/80 backdrop-blur-sm border border-border/50 rounded-none p-4 mb-6">
        <h2 className="text-base font-semibold text-foreground mb-3">Sync Options</h2>
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Email events are automatically synced to your timeline. You can trigger a manual sync at any time.
          </p>
          <div className="flex items-center gap-2">
            <Button
              onClick={() => handleSync()}
              disabled={syncing || !account.is_active}
              variant="secondary"
              size="md"
            >
              {syncing ? (
                <>
                  <LoadingIcon />
                  Syncing...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4" />
                  Sync Now
                </>
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="bg-card/80 backdrop-blur-sm border border-red-200 dark:border-red-800 rounded-none p-4">
        <h2 className="text-base font-semibold text-red-600 dark:text-red-400 mb-3">Danger Zone</h2>
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Disconnecting this email account will stop syncing emails. Existing email events will remain in your timeline.
          </p>
          <Button onClick={() => setConfirmingDelete(true)} disabled={deleting} variant="secondary" size="md">
            {deleting ? (
              <>
                <LoadingIcon />
                Disconnecting...
              </>
            ) : (
              <>
                <Trash2 className="w-4 h-4" />
                Disconnect Account
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmModal
        isOpen={confirmingDelete}
        onClose={() => setConfirmingDelete(false)}
        title="Disconnect Email Account?"
        message={`Are you sure you want to disconnect "${account.email_address}"? This will stop syncing emails. Existing email events will remain in your timeline.`}
        confirmText="Disconnect"
        cancelText="Cancel"
        isDestructive={true}
        onConfirm={handleDelete}
      />
    </>
  )
}
