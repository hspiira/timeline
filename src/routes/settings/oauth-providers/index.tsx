import { createFileRoute } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import {
  Activity,
  CheckCircle,
  Cloud,
  Copy,
  ExternalLink,
  Eye,
  EyeOff,
  Key,
  Loader2,
  Mail,
  Plus,
  SquarePen,
  Trash2,
  XCircle,
} from 'lucide-react'
import { useCallback, useEffect, useId, useState } from 'react'
import { Button } from '@/components/ui/button'
import { ConfirmModal } from '@/components/ui/ConfirmModal'
import { DataTable } from '@/components/ui/DataTable'
import { FormError } from '@/components/ui/FormField'
import { Modal } from '@/components/ui/Modal'
import { useFetchWithError } from '@/hooks/useFetchWithError'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { useToast } from '@/hooks/useToast'
import { timelineApi } from '@/lib/api-client'
import { getApiErrorMessage } from '@/lib/api-utils'
import type { components } from '@/lib/timeline-api'

export const Route = createFileRoute('/settings/oauth-providers/')({
  component: OAuthProvidersPage,
})

type OAuthProviderConfig = components['schemas']['OAuthConfigResponse']
type OAuthProviderCreate = components['schemas']['OAuthConfigCreateRequest']
type OAuthProviderUpdate = components['schemas']['OAuthConfigUpdate']

const PROVIDER_INFO: Record<
  string,
  { name: string; icon: typeof Mail; color: string; defaultScopes: string[] }
> = {
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
  const includeInactiveId = useId()
  const authState = useRequireAuth()
  const toast = useToast()
  const [providers, setProviders] = useState<OAuthProviderConfig[]>([])
  const [includeInactive, setIncludeInactive] = useState(false)

  const fetchProviders = useCallback(async () => {
    const r = await timelineApi.oauthProviders.list({ include_inactive: includeInactive })
    return r.error != null ? { error: r.error, response: r.response } : { data: r.data || [] }
  }, [includeInactive])

  const {
    data: fetchedProviders,
    error,
    loading,
    hasNoAccess,
    refetch,
    setError,
  } = useFetchWithError<OAuthProviderConfig[]>(fetchProviders, {
    defaultErrorMessage: 'Unable to load OAuth providers',
    enabled: !!authState.user,
  })

  useEffect(() => {
    if (authState.user) refetch()
  }, [authState.user, includeInactive, refetch])

  useEffect(() => {
    if (fetchedProviders) setProviders(fetchedProviders)
  }, [fetchedProviders])

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingProvider, setEditingProvider] = useState<OAuthProviderConfig | null>(null)
  const [deletingProviderId, setDeletingProviderId] = useState<string | null>(null)
  const [confirmingDelete, setConfirmingDelete] = useState<{ id: string; name: string } | null>(
    null,
  )
  const [checkingHealth, setCheckingHealth] = useState<string | null>(null)

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
        const errorMsg = getApiErrorMessage(apiError, 'Failed to delete OAuth provider')
        setError(errorMsg)
        toast.error('Failed to delete', errorMsg)
        throw new Error(errorMsg)
      }

      setProviders((prev) => prev.filter((p) => p.id !== confirmingDelete.id))
      toast.success('Provider deleted', `"${confirmingDelete.name}" has been deleted`)
    } finally {
      setDeletingProviderId(null)
    }
  }

  const handleCheckHealth = async (provider: OAuthProviderConfig) => {
    setCheckingHealth(provider.id)
    try {
      const { data, error: apiError } = await timelineApi.oauthProviders.getHealth(provider.id)

      if (apiError) {
        toast.error(
          'Health check failed',
          getApiErrorMessage(apiError, 'Could not check provider health'),
        )
      } else if (data) {
        if (data.health_status === 'healthy') {
          toast.success('Provider healthy', `${provider.display_name} is operational`)
        } else {
          toast.warning('Provider issue', data.last_health_error || 'Provider may have issues')
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
        const info = PROVIDER_INFO[provider.provider_type] || {
          name: provider.provider_type,
          icon: Key,
          color: 'text-gray-600',
        }
        const Icon = info.icon
        return (
          <div className="flex items-center gap-2">
            <div className={`p-1.5 rounded-none bg-accent ${info.color}`}>
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
      id: 'health',
      header: 'Health',
      cell: ({ row }) => {
        const status = row.original.health_status
        if (status === 'healthy') {
          return (
            <div className="flex items-center gap-1 text-green-600 dark:text-green-400">
              <CheckCircle className="w-3 h-3" />
              <span className="text-xs">Healthy</span>
            </div>
          )
        }
        if (status) {
          return <span className="text-xs text-amber-600 dark:text-amber-400">{status}</span>
        }
        return <span className="text-xs text-muted-foreground">—</span>
      },
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
              prev.map((p) => (p.id === updatedProvider.id ? updatedProvider : p)),
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
        <div className="mb-3 p-3 bg-amber-50 dark:bg-amber-900/40 border border-amber-200 dark:border-amber-700 rounded-none flex gap-2">
          <div className="flex-1">
            <h3 className="font-semibold text-amber-900 dark:text-amber-100 text-sm">
              Limited Access
            </h3>
            <p className="text-sm text-amber-800 dark:text-amber-200 mt-0.5">
              You don't have permission to manage OAuth providers. You can view but cannot create or
              modify.
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
      <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-none">
        <h3 className="font-semibold text-blue-900 dark:text-blue-100 text-sm mb-1">
          Setup Instructions
        </h3>
        <p className="text-sm text-blue-800 dark:text-blue-200">
          To enable OAuth for email providers, you need to create OAuth credentials in the
          provider's developer console:
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
      <div className="mb-3 p-2.5 bg-card/80 backdrop-blur-sm rounded-none border border-border/50 flex items-center gap-2">
        <input
          type="checkbox"
          id={includeInactiveId}
          checked={includeInactive}
          onChange={(e) => setIncludeInactive(e.target.checked)}
          className="w-4 h-4 rounded-none border-input"
        />
        <label htmlFor={includeInactiveId} className="text-sm text-foreground cursor-pointer">
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
      <ConfirmModal
        isOpen={!!confirmingDelete}
        onClose={() => setConfirmingDelete(null)}
        title="Delete OAuth Provider?"
        message={`Are you sure you want to delete "${confirmingDelete?.name}"? Existing email accounts using this provider will continue to work, but new connections won't be possible.`}
        confirmText="Delete"
        cancelText="Cancel"
        isDestructive={true}
        onConfirm={handleConfirmDelete}
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
  const clientIdId = useId()
  const clientSecretId = useId()
  const displayNameId = useId()
  const providerTypeId = useId()
  const redirectUriId = useId()
  const scopesOnePerId = useId()
  const [providerType, setProviderType] = useState(provider?.provider_type || 'gmail')
  const [clientId, setClientId] = useState('')
  const [clientSecret, setClientSecret] = useState('')
  const [redirectUri, setRedirectUri] = useState(
    `${window.location.origin.replace(':3000', ':8000')}/api/oauth-providers/${providerType}/callback`,
  )
  const [scopes, setScopes] = useState<string>(
    provider ? '' : (PROVIDER_INFO[providerType]?.defaultScopes || []).join('\n'),
  )
  const [displayName, setDisplayName] = useState(provider?.display_name || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showSecret, setShowSecret] = useState(false)

  // Update redirect URI when provider type changes (only for new providers)
  useEffect(() => {
    if (!provider) {
      setRedirectUri(
        `${window.location.origin.replace(':3000', ':8000')}/api/oauth-providers/${providerType}/callback`,
      )
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
        // Update existing provider — OAuthConfigUpdate only supports display_name,
        // redirect_uri, redirect_uri_whitelist, allowed_scopes, default_scopes, tenant_configured_scopes
        const updateData: OAuthProviderUpdate = {}

        if (displayName.trim() && displayName.trim() !== provider.display_name) {
          updateData.display_name = displayName.trim()
        }
        if (redirectUri.trim()) {
          updateData.redirect_uri = redirectUri.trim()
        }
        if (scopes.trim()) {
          updateData.tenant_configured_scopes = scopes
            .split('\n')
            .map((s) => s.trim())
            .filter(Boolean)
        }

        const { data, error: apiError } = await timelineApi.oauthProviders.update(
          provider.id,
          updateData,
        )

        if (apiError) {
          const errorMsg = getApiErrorMessage(apiError, 'Failed to update OAuth provider')
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
          scopes: scopes.trim()
            ? scopes
                .split('\n')
                .map((s) => s.trim())
                .filter(Boolean)
            : undefined,
        }

        const { data, error: apiError } = await timelineApi.oauthProviders.create(createData)

        if (apiError) {
          const errorMsg = getApiErrorMessage(apiError, 'Failed to create OAuth provider')
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

  const info = PROVIDER_INFO[providerType] || {
    name: providerType,
    icon: Key,
    color: 'text-gray-600',
  }
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
            <label
              htmlFor={providerTypeId}
              className="block text-sm font-medium text-foreground/90 mb-2"
            >
              Provider Type <span className="text-destructive">*</span>
            </label>
            <div id={providerTypeId} className="grid grid-cols-2 gap-2">
              {Object.entries(PROVIDER_INFO).map(([type, typeInfo]) => {
                const TypeIcon = typeInfo.icon
                return (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setProviderType(type)}
                    className={`p-3 border rounded-none text-left transition-colors ${
                      providerType === type
                        ? 'border-primary bg-primary/10'
                        : 'border-border hover:border-primary/50'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <div className={`p-1.5 rounded-none bg-accent ${typeInfo.color}`}>
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
          <div className="flex items-center gap-2 p-3 bg-muted rounded-none">
            <div className={`p-1.5 rounded-none bg-accent ${info.color}`}>
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
          <label htmlFor={clientIdId} className="block text-sm font-medium text-foreground/90 mb-2">
            Client ID {!provider && <span className="text-destructive">*</span>}
          </label>
          <input
            id={clientIdId}
            type="text"
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            placeholder={provider ? '(unchanged)' : 'e.g., 123456789.apps.googleusercontent.com'}
            className="w-full px-3 py-2 bg-background border border-input rounded-none text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 font-mono text-sm"
            disabled={loading}
          />
        </div>

        {/* Client Secret */}
        <div>
          <label
            htmlFor={clientSecretId}
            className="block text-sm font-medium text-foreground/90 mb-2"
          >
            Client Secret {!provider && <span className="text-destructive">*</span>}
          </label>
          <div id={clientSecretId} className="relative">
            <input
              type={showSecret ? 'text' : 'password'}
              value={clientSecret}
              onChange={(e) => setClientSecret(e.target.value)}
              placeholder={provider ? '(unchanged)' : 'Your client secret'}
              className="w-full px-3 py-2 pr-10 bg-background border border-input rounded-none text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 font-mono text-sm"
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
          <label
            htmlFor={redirectUriId}
            className="block text-sm font-medium text-foreground/90 mb-2"
          >
            Redirect URI {!provider && <span className="text-destructive">*</span>}
          </label>
          <div id={redirectUriId} className="relative">
            <input
              type="text"
              value={redirectUri}
              onChange={(e) => setRedirectUri(e.target.value)}
              placeholder="https://your-api.com/api/oauth-providers/gmail/callback"
              className="w-full px-3 py-2 pr-10 bg-background border border-input rounded-none text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 font-mono text-sm"
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
          <label
            htmlFor={scopesOnePerId}
            className="block text-sm font-medium text-foreground/90 mb-2"
          >
            Scopes <span className="text-muted-foreground">(one per line)</span>
          </label>
          <textarea
            id={scopesOnePerId}
            value={scopes}
            onChange={(e) => setScopes(e.target.value)}
            placeholder="Leave empty for default scopes"
            rows={3}
            className="w-full px-3 py-2 bg-background border border-input rounded-none text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 font-mono text-sm"
            disabled={loading}
          />
        </div>

        {/* Display Name (only for editing) */}
        {provider && (
          <div>
            <label
              htmlFor={displayNameId}
              className="block text-sm font-medium text-foreground/90 mb-2"
            >
              Display Name
            </label>
            <input
              id={displayNameId}
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder={provider.display_name}
              className="w-full px-3 py-2 bg-background border border-input rounded-none text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              disabled={loading}
            />
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
          <Button type="submit" disabled={loading} className="w-full sm:w-auto">
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {provider ? 'Update Provider' : 'Create Provider'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
