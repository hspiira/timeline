import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { useToast } from '@/hooks/useToast'
import { timelineApi } from '@/lib/api-client'
import { getApiErrorDisplay, isAuthOrPermissionError } from '@/lib/api-utils'
import {
  AlertCircle,
  Loader2,
  Plus,
  Trash2,
  Eye,
  X,
} from 'lucide-react'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import type { components } from '@/lib/timeline-api'

export const Route = createFileRoute('/admin/permissions/')({
  component: PermissionsPage,
})

type PermissionResponse = components['schemas']['PermissionResponse']
type RoleResponse = components['schemas']['RoleResponse']

const RESOURCE_TYPES = [
  'event',
  'subject',
  'role',
  'permission',
  'workflow',
  'document',
  'user',
  'tenant',
]

const ACTION_TYPES = ['create', 'read', 'update', 'delete', 'assign', 'verify']

function PermissionsPage() {
  const authState = useRequireAuth()
  const toast = useToast()
  const [permissions, setPermissions] = useState<PermissionResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hasNoAccess, setHasNoAccess] = useState(false)

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [deletingPermId, setDeletingPermId] = useState<string | null>(null)
  const [confirmingDelete, setConfirmingDelete] = useState<{ id: string; code: string } | null>(null)
  const [filterResource, setFilterResource] = useState('')
  const [viewingRoles, setViewingRoles] = useState<{ permId: string; permCode: string; roles: RoleResponse[] } | null>(null)
  const [_loadingRoles, _setLoadingRoles] = useState(false)

  useEffect(() => {
    if (authState.user) {
      fetchPermissions()
    }
  }, [authState.user])

  const fetchPermissions = async () => {
    setLoading(true)
    setError(null)
    setHasNoAccess(false)

    try {
      const { data, error: apiError, response } = await timelineApi.permissions.list({
        skip: 0,
        limit: 1000,
      })

      if (apiError) {
        const display = getApiErrorDisplay(
          { error: apiError, status: response?.status },
          'Unable to load permissions'
        )
        setHasNoAccess(isAuthOrPermissionError(display, response?.status))
        setError(display.message)
      } else {
        setPermissions(data || [])
      }
    } catch (err) {
      setError('An unexpected error occurred')
      console.error('Error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteClick = (perm: PermissionResponse) => {
    if (hasNoAccess) {
      toast.error('Permission denied', 'You do not have permission to delete permissions')
      return
    }
    setConfirmingDelete({ id: perm.id, code: perm.code })
  }

  const handleConfirmDelete = async () => {
    if (!confirmingDelete) return

    setDeletingPermId(confirmingDelete.id)
    try {
      const { error: apiError } = await timelineApi.permissions.delete(confirmingDelete.id)

      if (apiError) {
        const errorMsg = // @ts-ignore
          apiError?.message || 'Failed to delete permission'
        setError(errorMsg)
        toast.error('Failed to delete', errorMsg)
      } else {
        setPermissions((prev) => prev.filter((p) => p.id !== confirmingDelete.id))
        toast.success('Permission deleted', `"${confirmingDelete.code}" has been deleted`)
        setConfirmingDelete(null)
      }
    } finally {
      setDeletingPermId(null)
    }
  }

  const filteredPermissions = filterResource
    ? permissions.filter((p) => p.resource === filterResource)
    : permissions

  if (!authState.user) {
    return null
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>Loading permissions...</span>
        </div>
      </div>
    )
  }

  return (
    <>
      {/* Create Modal */}
      {showCreateModal && (
        <PermissionFormModal
          resources={RESOURCE_TYPES}
          actions={ACTION_TYPES}
          onClose={() => setShowCreateModal(false)}
          onSuccess={(newPerm) => {
            setPermissions((prev) => [...prev, newPerm])
            setShowCreateModal(false)
            setError(null)
          }}
          onError={setError}
        />
      )}

      {/* View Roles Modal */}
      {viewingRoles && (
        <ViewRolesModal
          permCode={viewingRoles.permCode}
          roles={viewingRoles.roles}
          loading={_loadingRoles}
          onClose={() => setViewingRoles(null)}
        />
      )}

      {/* Error Alert */}
      {error && (
        <div className="mb-3 p-2.5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-none flex gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="font-semibold text-red-900 dark:text-red-200 text-sm">Error</h3>
            <p className="text-sm text-red-800 dark:text-red-300 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Limited Access Warning */}
      {hasNoAccess && (
        <div className="mb-3 p-2.5 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-none flex gap-2">
          <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="font-semibold text-amber-900 dark:text-amber-200 text-sm">
              Limited Access
            </h3>
            <p className="text-sm text-amber-800 dark:text-amber-300 mt-0.5">
              You don't have permission to manage permissions. You can view but cannot create or
              modify.
            </p>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <h1 className="text-lg font-bold text-foreground">Permissions</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Manage system permissions ({permissions.length} total)
          </p>
        </div>
        {!hasNoAccess && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded-none font-medium hover:bg-primary/90 transition-colors"
          >
            <Plus className="w-3 h-3" />
            Create Permission
          </button>
        )}
      </div>

      {/* Filter */}
      <div className="mb-3 p-2.5 bg-card/80 backdrop-blur-sm rounded-none border border-border/50">
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-sm font-medium text-foreground/90">Filter by resource:</label>
          <select
            value={filterResource}
            onChange={(e) => setFilterResource(e.target.value)}
            className="px-3 py-1.5 bg-background border border-input rounded-none text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="">All Resources</option>
            {RESOURCE_TYPES.map((resource) => (
              <option key={resource} value={resource}>
                {resource}
              </option>
            ))}
          </select>
          {filterResource && (
            <button
              onClick={() => setFilterResource('')}
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              Clear filter
            </button>
          )}
        </div>
      </div>

      {/* Permissions Table */}
      {filteredPermissions.length === 0 ? (
        <div className="text-center py-8 bg-card/80 rounded-none border border-border/50 p-4">
          <h3 className="text-sm font-semibold text-foreground mb-1">
            {filterResource ? `No ${filterResource} permissions` : 'No permissions yet'}
          </h3>
          <p className="text-sm text-muted-foreground mb-3">
            {hasNoAccess ? 'You do not have permission to view permissions.' : 'Create your first permission'}
          </p>
          {!hasNoAccess && !filterResource && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded-none font-medium hover:bg-primary/90 transition-colors"
            >
              <Plus className="w-3 h-3" />
              Create Permission
            </button>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto bg-card/80 rounded-none border border-border/50">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 px-2.5 font-medium text-muted-foreground text-sm">
                  RESOURCE
                </th>
                <th className="text-left py-2 px-2.5 font-medium text-muted-foreground text-sm">
                  ACTION
                </th>
                <th className="text-left py-2 px-2.5 font-medium text-muted-foreground text-sm">
                  CODE
                </th>
                <th className="text-left py-2 px-2.5 font-medium text-muted-foreground text-sm">
                  DESCRIPTION
                </th>
                <th className="text-right py-2 px-2.5 font-medium text-muted-foreground text-sm">
                  ACTIONS
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredPermissions.map((perm) => (
                <tr
                  key={perm.id}
                  className="border-b border-border hover:bg-muted/50 transition-colors"
                >
                  <td className="py-2 px-2.5">
                    <span className="text-xs px-1.5 py-0.5 bg-secondary text-muted-foreground rounded-none font-medium capitalize">
                      {perm.resource}
                    </span>
                  </td>
                  <td className="py-2 px-2.5">
                    <span className="text-xs px-1.5 py-0.5 bg-secondary text-muted-foreground rounded-none font-medium capitalize">
                      {perm.action}
                    </span>
                  </td>
                  <td className="py-2 px-2.5">
                    <span className="font-mono text-foreground font-medium">{perm.code}</span>
                  </td>
                  <td className="py-2 px-2.5 text-muted-foreground text-sm max-w-sm truncate">
                    {perm.description || '-'}
                  </td>
                  <td className="py-2 px-2.5 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setViewingRoles({ permId: perm.id, permCode: perm.code, roles: [] })}
                        disabled={hasNoAccess}
                        title={hasNoAccess ? 'No permission' : 'View roles with this permission'}
                        className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteClick(perm)}
                        disabled={deletingPermId === perm.id || hasNoAccess}
                        title={
                          hasNoAccess
                            ? 'No permission'
                            : 'Delete'
                        }
                        className="p-1 text-muted-foreground hover:text-red-600 dark:hover:text-red-400 hover:bg-muted rounded-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {deletingPermId === perm.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={!!confirmingDelete}
        title="Delete Permission?"
        message={`Are you sure you want to delete "${confirmingDelete?.code}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        isDestructive={true}
        isLoading={deletingPermId === confirmingDelete?.id}
        onConfirm={handleConfirmDelete}
        onCancel={() => setConfirmingDelete(null)}
      />
    </>
  )
}

// Permission Form Modal Component
function PermissionFormModal({
  resources,
  actions,
  onClose,
  onSuccess,
  onError,
}: {
  resources: string[]
  actions: string[]
  onClose: () => void
  onSuccess: (permission: PermissionResponse) => void
  onError: (error: string) => void
}) {
  const [resource, setResource] = useState('')
  const [action, setAction] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!resource.trim()) {
      setError('Resource is required')
      return
    }

    if (!action.trim()) {
      setError('Action is required')
      return
    }

    setLoading(true)
    try {
      const { data, error: apiError } = await timelineApi.permissions.create({
        resource: resource.trim(),
        action: action.trim(),
        code: `${resource}:${action}`,
        description: description.trim() || null,
      })

      if (apiError) {
        const errorMsg = // @ts-ignore
          apiError?.message || 'Failed to create permission'
        setError(errorMsg)
        onError(errorMsg)
      } else if (data) {
        onSuccess(data)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-background border border-border rounded-none max-w-2xl w-full max-h-[90vh] overflow-auto p-6 shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-foreground">Create Permission</h2>
          <button
            onClick={onClose}
            disabled={loading}
            className="p-1 text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-none flex gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
            </div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-foreground/90 mb-2">
              Resource <span className="text-destructive">*</span>
            </label>
            <select
              value={resource}
              onChange={(e) => setResource(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-input rounded-none text-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              disabled={loading}
            >
              <option value="">Select resource...</option>
              {resources.map((res) => (
                <option key={res} value={res}>
                  {res}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground/90 mb-2">
              Action <span className="text-destructive">*</span>
            </label>
            <select
              value={action}
              onChange={(e) => setAction(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-input rounded-none text-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              disabled={loading}
            >
              <option value="">Select action...</option>
              {actions.map((act) => (
                <option key={act} value={act}>
                  {act}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground/90 mb-2">
              Generated Code
            </label>
            <input
              type="text"
              value={resource && action ? `${resource}:${action}` : ''}
              readOnly
              className="w-full px-3 py-2 bg-background border border-input rounded-none text-foreground/70 disabled:opacity-50"
              placeholder="Format: resource:action"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground/90 mb-2">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this permission grants..."
              rows={3}
              className="w-full px-3 py-2 bg-background border border-input rounded-none text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              disabled={loading}
            />
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted rounded-none transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !resource || !action}
              className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-none hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              Create Permission
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// View Roles Modal
function ViewRolesModal({
  permCode,
  roles,
  loading,
  onClose,
}: {
  permCode: string
  roles: RoleResponse[]
  loading: boolean
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-background border border-border rounded-none max-w-2xl w-full max-h-[90vh] overflow-auto p-6 shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold text-foreground">Roles with Permission</h2>
            <p className="text-sm text-muted-foreground mt-0.5 font-mono">{permCode}</p>
          </div>
          <button
            onClick={onClose}
            disabled={loading}
            className="p-1 text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Loading roles...</span>
            </div>
          </div>
        ) : roles.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-sm text-muted-foreground">No roles have this permission</p>
          </div>
        ) : (
          <div className="space-y-2">
            {roles.map((role) => (
              <div
                key={role.id}
                className="p-3 bg-muted rounded-none border border-border flex items-center justify-between"
              >
                <div>
                  <p className="font-semibold text-foreground">{role.name}</p>
                  {role.description && (
                    <p className="text-xs text-muted-foreground mt-0.5">{role.description}</p>
                  )}
                </div>
                {role.is_system && (
                  <span className="text-xs px-1.5 py-0.5 bg-primary/20 text-primary rounded-none font-medium">
                    SYSTEM
                  </span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Close Button */}
        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-none hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
