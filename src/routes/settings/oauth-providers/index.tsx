import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { useToast } from '@/hooks/useToast'
import { timelineApi } from '@/lib/api-client'
import {
  Plus,
  Trash2,
  SquarePen,
  CheckCircle,
  XCircle,
  Loader2,
  Key,
  Activity,
  Mail,
  Cloud,
  ExternalLink,
  Eye,
  EyeOff,
  Copy,
} from 'lucide-react'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Modal } from '@/components/ui/Modal'
import { FormError } from '@/components/ui/FormField'
import { Button } from '@/components/ui/button'
import { DataTable } from '@/components/ui/DataTable'
import type { components } from '@/lib/timeline-api'

export const Route = createFileRoute('/settings/oauth-providers/')({
  component: OAuthProvidersPage,
})

type OAuthProviderConfig = components['schemas']['OAuthProviderConfigResponse']
type OAuthProviderCreate = components['schemas']['OAuthProviderConfigCreate']
type OAuthProviderUpdate = components['schemas']['OAuthProviderConfigUpdate']

const PROVIDER_INFO: Record<string, { name: string; icon: typeof Mail; color: string; defaultScopes: string[] }> = {
  gmail: {
    name: 'Gmail',
    icon: Mail,
    color: 'text-red-600 dark:text-red-400',
    defaultScopes: ['https://mail.google.com/', 'https://www.googleapis.com/auth/gmail.readonly'],
  },
  outlook: {
    name: 'Outlook',
    icon: Cloud,
    color: 'text-blue-600 dark:text-blue-400',
    defaultScopes: ['https://outlook.office.com/IMAP.AccessAsUser.All', 'offline_access'],
  },
}

function OAuthProvidersPage() {
  const authState = useRequireAuth()
  const toast = useToast()
  const [providers, setProviders] = useState<OAuthProviderConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hasNoAccess, setHasNoAccess] = useState(false)

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingProvider, setEditingProvider] = useState<OAuthProviderConfig | null>(null)
  const [deletingProviderId, setDeletingProviderId] = useState<string | null>(null)
  const [confirmingDelete, setConfirmingDelete] = useState<{ id: string; name: string } | null>(null)
  const [includeInactive, setIncludeInactive] = useState(false)
  const [checkingHealth, setCheckingHealth] = useState<string | null>(null)

  useEffect(() => {
    if (authState.user) {
      fetchProviders()
    }
  }, [authState.user, includeInactive])

  const fetchProviders = async () => {
    setLoading(true)
    setError(null)
    setHasNoAccess(false)

    try {
      const { data, error: apiError } = await timelineApi.oauthProviders.list({
        include_inactive: includeInactive,
      })

      if (apiError) {
        const errorStr = JSON.stringify(apiError).toLowerCase()
        const isNoAccess =
          errorStr.includes('permission') ||
          errorStr.includes('401') ||
          errorStr.includes('403') ||
          errorStr.includes('unauthorized')
        setHasNoAccess(isNoAccess)
        const errorMsg =
          (apiError as any)?.message || (isNoAccess ? 'No permission to view OAuth providers' : 'Unable to load OAuth providers')
        setError(errorMsg)
      } else {
        setProviders(data?.providers || [])
      }
    } catch (err) {
      setError('An unexpected error occurred')
      console.error('Error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteClick = (provider: OAuthProviderConfig) => {
    if (hasNoAccess) {
      toast.error('Permission denied', 'You do not have permission to delete OAuth providers')
      return
    }

    setConfirmingDelete({ id: provider.id, name: provider.display_name })
  }

  const handleConfirmDelete = async () => {
    if (!confirmingDelete) return

    setDeletingProviderId(confirmingDelete.id)
    try {
      const { error: apiError } = await timelineApi.oauthProviders.delete(confirmingDelete.id)

      if (apiError) {
        const errorMsg = (apiError as any)?.message || 'Failed to delete OAuth provider'
        setError(errorMsg)
        toast.error('Failed to delete', errorMsg)
      } else {
        setProviders((prev) => prev.filter((p) => p.id !== confirmingDelete.id))
        toast.success('Provider deleted', `"${confirmingDelete.name}" has been deleted`)
        setConfirmingDelete(null)
      }
    } finally {
      setDeletingProviderId(null)
    }
  }

  const handleCheckHealth = async (provider: OAuthProviderConfig) => {
    setCheckingHealth(provider.id)
    try {
      const { data, error: apiError } = await timelineApi.oauthProviders.getHealth(provider.id)

      if (apiError) {
        toast.error('Health check failed', (apiError as any)?.message || 'Could not check provider health')
      } else if (data) {
        if (data.is_operational) {
          toast.success('Provider healthy', `${provider.display_name} is operational`)
        } else {
          toast.warning('Provider issue', data.last_error || 'Provider may have issues')
        }
      }
    } finally {
      setCheckingHealth(null)
    }
  }

  if (!authState.user) {
    return null
  }

  const columns: ColumnDef<OAuthProviderConfig>[] = [
    {
      accessorKey: 'provider_type',
      header: 'Provider',
      cell: ({ row }) => {
        const provider = row.original
        const info = PROVIDER_INFO[provider.provider_type] || { name: provider.provider_type, icon: Key, color: 'text-gray-600' }
        const Icon = info.icon
        return (
          <div className="flex items-center gap-2">
            <div className={`p-1.5 rounded-xs bg-accent ${info.color}`}>
              <Icon className="w-4 h-4" />
            </div>
            <div>
              <span className="font-semibold text-foreground">{info.name}</span>
              <p className="text-xs text-muted-foreground">v{provider.version}</p>
            </div>
          </div>
        )
      },
    },
    {
      accessorKey: 'display_name',
      header: 'Display Name',
      cell: ({ row }) => (
        <span className="text-foreground text-sm">{row.original.display_name}</span>
      ),
    },
    {
      accessorKey: 'redirect_uri',
      header: 'Redirect URI',
      cell: ({ row }) => (
        <span className="text-xs text-muted-foreground font-mono truncate max-w-[200px] block">
          {row.original.redirect_uri}
        </span>
      ),
    },
    {
      id: 'rate_limit',
      header: 'Rate Limit',
      cell: ({ row }) => (
        <span className="text-xs text-muted-foreground">
          {row.original.current_hour_connections}/{row.original.rate_limit_connections_per_hour}/hr
        </span>
      ),
    },
    {
      id: 'status',
      header: 'Status',
      cell: ({ row }) =>
        row.original.is_active ? (
          <div className="flex items-center gap-1 text-green-600 dark:text-green-400">
            <CheckCircle className="w-3 h-3" />
            <span className="text-xs">Active</span>
          </div>
        ) : (
          <div className="flex items-center gap-1 text-muted-foreground">
            <XCircle className="w-3 h-3" />
            <span className="text-xs">Inactive</span>
          </div>
        ),
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => {
        const provider = row.original
        return (
          <div className="flex items-center justify-end gap-0.5">
            <Button
              onClick={() => handleCheckHealth(provider)}
              disabled={checkingHealth === provider.id || hasNoAccess}
              title="Check health"
              size="sm"
              variant="ghost"
            >
              {checkingHealth === provider.id ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Activity className="w-4 h-4" />
              )}
            </Button>
            <Button
              onClick={() => setEditingProvider(provider)}
              disabled={hasNoAccess}
              title={hasNoAccess ? 'No permission' : 'Edit'}
              size="sm"
              variant="ghost"
            >
              <SquarePen className="w-4 h-4" />
            </Button>
            <Button
              onClick={() => handleDeleteClick(provider)}
              disabled={deletingProviderId === provider.id || hasNoAccess}
              title={hasNoAccess ? 'No permission' : 'Delete'}
              size="sm"
              variant="ghost"
            >
              {deletingProviderId === provider.id ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Trash2 className="w-4 h-4 text-red-500" />
              )}
            </Button>
          </div>
        )
      },
    },
  ]

  return (
    <>
      {/* Create Modal */}
      {showCreateModal && (
        <OAuthProviderFormModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={(newProvider) => {
            setProviders((prev) => [...prev, newProvider])
            setShowCreateModal(false)
            setError(null)
            toast.success('Provider created', `${newProvider.display_name} has been configured`)
          }}
          onError={setError}
        />
      )}

      {/* Edit Modal */}
      {editingProvider && (
        <OAuthProviderFormModal
          provider={editingProvider}
          onClose={() => setEditingProvider(null)}
          onSuccess={(updatedProvider) => {
            setProviders((prev) =>
              prev.map((p) => (p.id === updatedProvider.id ? updatedProvider : p))
            )
            setEditingProvider(null)
            setError(null)
            toast.success('Provider updated', `${updatedProvider.display_name} has been updated`)
          }}
          onError={setError}
        />
      )}

      {/* Error Alert */}
      {error && <FormError message={error} />}

      {/* Limited Access Warning */}
      {hasNoAccess && (
        <div className="mb-3 p-3 bg-amber-50 dark:bg-amber-900/40 border border-amber-200 dark:border-amber-700 rounded-xs flex gap-2">
          <div className="flex-1">
            <h3 className="font-semibold text-amber-900 dark:text-amber-100 text-sm">
              Limited Access
            </h3>
            <p className="text-sm text-amber-800 dark:text-amber-200 mt-0.5">
              You don't have permission to manage OAuth providers. You can view but cannot create or modify.
            </p>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
        <div>
          <h1 className="text-lg font-bold text-foreground">OAuth Providers</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Configure OAuth credentials for Gmail, Outlook, and other email providers
          </p>
        </div>
        {!hasNoAccess && (
          <Button onClick={() => setShowCreateModal(true)} variant="primary">
            <Plus className="w-4 h-4" />
            Provider
          </Button>
        )}
      </div>

      {/* Info Box */}
      <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xs">
        <h3 className="font-semibold text-blue-900 dark:text-blue-100 text-sm mb-1">Setup Instructions</h3>
        <p className="text-sm text-blue-800 dark:text-blue-200">
          To enable OAuth for email providers, you need to create OAuth credentials in the provider's developer console:
        </p>
        <ul className="text-sm text-blue-800 dark:text-blue-200 mt-2 space-y-1 list-disc list-inside">
          <li>
            <strong>Gmail:</strong>{' '}
            <a
              href="https://console.cloud.google.com/apis/credentials"
              target="_blank"
              rel="noopener noreferrer"
              className="underline inline-flex items-center gap-1"
            >
              Google Cloud Console <ExternalLink className="w-3 h-3" />
            </a>
          </li>
          <li>
            <strong>Outlook:</strong>{' '}
            <a
              href="https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade"
              target="_blank"
              rel="noopener noreferrer"
              className="underline inline-flex items-center gap-1"
            >
              Azure Portal <ExternalLink className="w-3 h-3" />
            </a>
          </li>
        </ul>
      </div>

      {/* Filter */}
      <div className="mb-3 p-2.5 bg-card/80 backdrop-blur-sm rounded-xs border border-border/50 flex items-center gap-2">
        <input
          type="checkbox"
          id="includeInactive"
          checked={includeInactive}
          onChange={(e) => setIncludeInactive(e.target.checked)}
          className="w-4 h-4 rounded border-input"
        />
        <label htmlFor="includeInactive" className="text-sm text-foreground cursor-pointer">
          Show inactive providers
        </label>
      </div>

      {/* Providers Table */}
      <DataTable
        data={providers}
        columns={columns}
        isLoading={loading}
        isEmpty={providers.length === 0}
        compact={true}
        enablePagination={true}
        pageSize={10}
        emptyState={{
          title: 'No OAuth providers configured',
          description: hasNoAccess
            ? 'You do not have permission to view OAuth providers.'
            : 'Add OAuth credentials to enable email account connections via OAuth',
          action: !hasNoAccess ? (
            <Button onClick={() => setShowCreateModal(true)} variant="primary">
              <Plus className="w-4 h-4" />
              Add Provider
            </Button>
          ) : undefined,
        }}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={!!confirmingDelete}
        title="Delete OAuth Provider?"
        message={`Are you sure you want to delete "${confirmingDelete?.name}"? Existing email accounts using this provider will continue to work, but new connections won't be possible.`}
        confirmText="Delete"
        cancelText="Cancel"
        isDestructive={true}
        isLoading={deletingProviderId === confirmingDelete?.id}
        onConfirm={handleConfirmDelete}
        onCancel={() => setConfirmingDelete(null)}
      />
    </>
  )
}

// OAuth Provider Form Modal Component
function OAuthProviderFormModal({
  provider,
  onClose,
  onSuccess,
  onError,
}: {
  provider?: OAuthProviderConfig
  onClose: () => void
  onSuccess: (provider: OAuthProviderConfig) => void
  onError: (error: string) => void
}) {
  const [providerType, setProviderType] = useState(provider?.provider_type || 'gmail')
  const [clientId, setClientId] = useState('')
  const [clientSecret, setClientSecret] = useState('')
  const [redirectUri, setRedirectUri] = useState(
    provider?.redirect_uri || `${window.location.origin.replace(':3000', ':8000')}/api/oauth-providers/${providerType}/callback`
  )
  const [scopes, setScopes] = useState<string>(
    provider ? '' : (PROVIDER_INFO[providerType]?.defaultScopes || []).join('\n')
  )
  const [isActive, setIsActive] = useState(provider?.is_active ?? true)
  const [rateLimit, setRateLimit] = useState(provider?.rate_limit_connections_per_hour?.toString() || '100')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showSecret, setShowSecret] = useState(false)

  // Update redirect URI when provider type changes (only for new providers)
  useEffect(() => {
    if (!provider) {
      setRedirectUri(`${window.location.origin.replace(':3000', ':8000')}/api/oauth-providers/${providerType}/callback`)
      setScopes((PROVIDER_INFO[providerType]?.defaultScopes || []).join('\n'))
    }
  }, [providerType, provider])

  const handleCopyRedirectUri = () => {
    navigator.clipboard.writeText(redirectUri)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!provider) {
      if (!clientId.trim()) {
        setError('Client ID is required')
        return
      }
      if (!clientSecret.trim()) {
        setError('Client Secret is required')
        return
      }
      if (!redirectUri.trim()) {
        setError('Redirect URI is required')
        return
      }
    }

    setLoading(true)
    try {
      if (provider) {
        // Update existing provider
        const updateData: OAuthProviderUpdate = {
          is_active: isActive,
          rate_limit_connections_per_hour: parseInt(rateLimit, 10) || 100,
        }

        // Only include credentials if they were provided
        if (clientId.trim()) {
          updateData.client_id = clientId.trim()
        }
        if (clientSecret.trim()) {
          updateData.client_secret = clientSecret.trim()
        }
        if (redirectUri.trim() !== provider.redirect_uri) {
          updateData.redirect_uri = redirectUri.trim()
        }
        if (scopes.trim()) {
          updateData.scopes = scopes.split('\n').map(s => s.trim()).filter(Boolean)
        }

        const { data, error: apiError } = await timelineApi.oauthProviders.update(provider.id, updateData)

        if (apiError) {
          const errorMsg = (apiError as any)?.message || 'Failed to update OAuth provider'
          setError(errorMsg)
          onError(errorMsg)
        } else if (data) {
          onSuccess(data)
        }
      } else {
        // Create new provider
        const createData: OAuthProviderCreate = {
          provider_type: providerType,
          client_id: clientId.trim(),
          client_secret: clientSecret.trim(),
          redirect_uri: redirectUri.trim(),
          scopes: scopes.trim() ? scopes.split('\n').map(s => s.trim()).filter(Boolean) : undefined,
        }

        const { data, error: apiError } = await timelineApi.oauthProviders.create(createData)

        if (apiError) {
          const errorMsg = (apiError as any)?.message || 'Failed to create OAuth provider'
          setError(errorMsg)
          onError(errorMsg)
        } else if (data) {
          onSuccess(data)
        }
      }
    } finally {
      setLoading(false)
    }
  }

  const info = PROVIDER_INFO[providerType] || { name: providerType, icon: Key, color: 'text-gray-600' }
  const Icon = info.icon

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={provider ? 'Edit OAuth Provider' : 'Add OAuth Provider'}
      maxWidth="max-w-2xl"
      closeButton={!loading}
    >
      {/* Error Alert */}
      {error && <FormError message={error} />}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Provider Type */}
        {!provider && (
          <div>
            <label className="block text-sm font-medium text-foreground/90 mb-2">
              Provider Type <span className="text-destructive">*</span>
            </label>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(PROVIDER_INFO).map(([type, typeInfo]) => {
                const TypeIcon = typeInfo.icon
                return (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setProviderType(type)}
                    className={`p-3 border rounded-xs text-left transition-colors ${
                      providerType === type
                        ? 'border-primary bg-primary/10'
                        : 'border-border hover:border-primary/50'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <div className={`p-1.5 rounded-xs bg-accent ${typeInfo.color}`}>
                        <TypeIcon className="w-4 h-4" />
                      </div>
                      <span className="font-medium text-foreground">{typeInfo.name}</span>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Display current provider for editing */}
        {provider && (
          <div className="flex items-center gap-2 p-3 bg-muted rounded-xs">
            <div className={`p-1.5 rounded-xs bg-accent ${info.color}`}>
              <Icon className="w-4 h-4" />
            </div>
            <div>
              <span className="font-medium text-foreground">{info.name}</span>
              <p className="text-xs text-muted-foreground">Version {provider.version}</p>
            </div>
          </div>
        )}

        {/* Client ID */}
        <div>
          <label className="block text-sm font-medium text-foreground/90 mb-2">
            Client ID {!provider && <span className="text-destructive">*</span>}
          </label>
          <input
            type="text"
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            placeholder={provider ? '(unchanged)' : 'e.g., 123456789.apps.googleusercontent.com'}
            className="w-full px-3 py-2 bg-background border border-input rounded-xs text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 font-mono text-sm"
            disabled={loading}
          />
        </div>

        {/* Client Secret */}
        <div>
          <label className="block text-sm font-medium text-foreground/90 mb-2">
            Client Secret {!provider && <span className="text-destructive">*</span>}
          </label>
          <div className="relative">
            <input
              type={showSecret ? 'text' : 'password'}
              value={clientSecret}
              onChange={(e) => setClientSecret(e.target.value)}
              placeholder={provider ? '(unchanged)' : 'Your client secret'}
              className="w-full px-3 py-2 pr-10 bg-background border border-input rounded-xs text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 font-mono text-sm"
              disabled={loading}
            />
            <button
              type="button"
              onClick={() => setShowSecret(!showSecret)}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground"
            >
              {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Redirect URI */}
        <div>
          <label className="block text-sm font-medium text-foreground/90 mb-2">
            Redirect URI {!provider && <span className="text-destructive">*</span>}
          </label>
          <div className="relative">
            <input
              type="text"
              value={redirectUri}
              onChange={(e) => setRedirectUri(e.target.value)}
              placeholder="https://your-api.com/api/oauth-providers/gmail/callback"
              className="w-full px-3 py-2 pr-10 bg-background border border-input rounded-xs text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 font-mono text-sm"
              disabled={loading}
            />
            <button
              type="button"
              onClick={handleCopyRedirectUri}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground"
              title="Copy to clipboard"
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Copy this URI and add it to your OAuth app's authorized redirect URIs
          </p>
        </div>

        {/* Scopes */}
        <div>
          <label className="block text-sm font-medium text-foreground/90 mb-2">
            Scopes <span className="text-muted-foreground">(one per line)</span>
          </label>
          <textarea
            value={scopes}
            onChange={(e) => setScopes(e.target.value)}
            placeholder="Leave empty for default scopes"
            rows={3}
            className="w-full px-3 py-2 bg-background border border-input rounded-xs text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 font-mono text-sm"
            disabled={loading}
          />
        </div>

        {/* Rate Limit (only for editing) */}
        {provider && (
          <div>
            <label className="block text-sm font-medium text-foreground/90 mb-2">
              Rate Limit (connections/hour)
            </label>
            <input
              type="number"
              value={rateLimit}
              onChange={(e) => setRateLimit(e.target.value)}
              min="1"
              max="1000"
              className="w-full px-3 py-2 bg-background border border-input rounded-xs text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              disabled={loading}
            />
          </div>
        )}

        {/* Active Toggle (only for editing) */}
        {provider && (
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_active"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="w-4 h-4 rounded border-input"
              disabled={loading}
            />
            <label htmlFor="is_active" className="text-sm font-medium text-foreground cursor-pointer">
              Active (allow new connections)
            </label>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 justify-end flex-col sm:flex-row pt-2">
          <Button
            type="button"
            onClick={onClose}
            disabled={loading}
            variant="outline"
            className="w-full sm:w-auto"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={loading}
            className="w-full sm:w-auto"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {provider ? 'Update Provider' : 'Create Provider'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
