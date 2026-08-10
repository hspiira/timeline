import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState, useCallback } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { useToast } from '@/hooks/useToast'
import { useFetchWithError } from '@/hooks/useFetchWithError'
import { timelineApi } from '@/lib/api-client'
import {
  Loader2,
  Plus,
  Trash2,
  Eye,
} from 'lucide-react'
import { ConfirmModal } from '@/components/ui/ConfirmModal'
import { SingleSelectCombobox } from '@/components/ui/combobox'
import { Modal } from '@/components/ui/Modal'
import { FormError } from '@/components/ui/FormField'
import { Button } from '@/components/ui/button'
import { DataTable } from '@/components/ui/DataTable'
import type { components } from '@/lib/timeline-api'

export const Route = createFileRoute('/settings/permissions/')({
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

  const fetchPermissions = useCallback(async () => {
    const r = await timelineApi.permissions.list({ skip: 0, limit: 1000 })
    return r.error != null ? { error: r.error, response: r.response } : { data: r.data || [] }
  }, [])

  const {
    data: fetchedPermissions,
    error,
    loading,
    hasNoAccess,
    refetch,
    setError,
  } = useFetchWithError<PermissionResponse[]>(fetchPermissions, {
    defaultErrorMessage: 'Unable to load permissions',
    enabled: !!authState.user,
  })

  useEffect(() => {
    if (authState.user) refetch()
  }, [authState.user, refetch])

  useEffect(() => {
    if (fetchedPermissions) setPermissions(fetchedPermissions)
  }, [fetchedPermissions])

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [deletingPermId, setDeletingPermId] = useState<string | null>(null)
  const [confirmingDelete, setConfirmingDelete] = useState<{ id: string; code: string } | null>(null)
  const [filterResource, setFilterResource] = useState('')
  const [viewingRoles, setViewingRoles] = useState<{ permId: string; permCode: string; roles: RoleResponse[] } | null>(null)

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
        throw new Error(errorMsg)
      }

      setPermissions((prev) => prev.filter((p) => p.id !== confirmingDelete.id))
      toast.success('Permission deleted', `"${confirmingDelete.code}" has been deleted`)
    } catch (err) {
      throw err
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

  // Define columns for DataTable
  const columns: ColumnDef<PermissionResponse>[] = [
    {
      accessorKey: 'resource',
      header: 'Resource',
      cell: ({ row }) => (
        <span className="text-xs px-1.5 py-0.5 bg-secondary text-muted-foreground rounded-none font-medium capitalize">
          {row.original.resource}
        </span>
      ),
    },
    {
      accessorKey: 'action',
      header: 'Action',
      cell: ({ row }) => (
        <span className="text-xs px-1.5 py-0.5 bg-secondary text-muted-foreground rounded-none font-medium capitalize">
          {row.original.action}
        </span>
      ),
    },
    {
      accessorKey: 'code',
      header: 'Code',
      cell: ({ row }) => (
        <span className="font-mono text-foreground font-medium">{row.original.code}</span>
      ),
    },
    {
      accessorKey: 'description',
      header: 'Description',
      cell: ({ row }) => (
        <span className="text-muted-foreground text-sm max-w-sm truncate">
          {row.original.description || '-'}
        </span>
      ),
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => {
        const perm = row.original
        return (
          <div className="flex items-center justify-end gap-0.5">
            <Button
              onClick={() => setViewingRoles({ permId: perm.id, permCode: perm.code, roles: [] })}
              disabled={hasNoAccess}
              title={hasNoAccess ? 'No permission' : 'View roles with this permission'}
              size="sm"
              variant="ghost"
            >
              <Eye className="w-4 h-4" />
            </Button>
            <Button
              onClick={() => handleDeleteClick(perm)}
              disabled={deletingPermId === perm.id || hasNoAccess}
              title={hasNoAccess ? 'No permission' : 'Delete'}
              size="sm"
              variant="ghost"
            >
              {deletingPermId === perm.id ? (
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
          loading={loading}
          onClose={() => setViewingRoles(null)}
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
              You don't have permission to manage permissions. You can view but cannot create or
              modify.
            </p>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
        <div>
          <h1 className="text-lg font-bold text-foreground">Permissions</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Manage system permissions ({permissions.length} total)
          </p>
        </div>
        {!hasNoAccess && (
          <Button
            onClick={() => setShowCreateModal(true)}
            variant="primary"
          >
            <Plus className="w-4 h-4" />
            Permission
          </Button>
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
            <Button
              onClick={() => setFilterResource('')}
              variant="secondary"
              size="sm"
            >
              Clear filter
            </Button>
          )}
        </div>
      </div>

      {/* Permissions Table */}
      <DataTable
        data={filteredPermissions}
        columns={columns}
        isLoading={loading}
        isEmpty={filteredPermissions.length === 0}
        compact={true}
        enablePagination={true}
        pageSize={10}
        emptyState={{
          title: filterResource ? `No ${filterResource} permissions` : 'No permissions yet',
          description: hasNoAccess
            ? 'You do not have permission to view permissions.'
            : 'Create your first permission',
          action:
            !hasNoAccess && !filterResource ? (
              <Button onClick={() => setShowCreateModal(true)} variant="primary">
                <Plus className="w-4 h-4" />
                Permission
              </Button>
            ) : undefined,
        }}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmModal
        isOpen={!!confirmingDelete}
        onClose={() => setConfirmingDelete(null)}
        title="Delete Permission?"
        message={`Are you sure you want to delete "${confirmingDelete?.code}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        isDestructive={true}
        onConfirm={handleConfirmDelete}
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
    <Modal
      isOpen={true}
      onClose={onClose}
      title="Create Permission"
      maxWidth="max-w-2xl"
      closeButton={!loading}
    >
      {/* Error Alert */}
      {error && <FormError message={error} />}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-foreground/90 mb-2">
              Resource <span className="text-destructive">*</span>
            </label>
            <SingleSelectCombobox
              value={resource}
              onValueChange={setResource}
              options={[
                { value: '', label: 'Select resource...' },
                ...resources.map((res) => ({ value: res, label: res })),
              ]}
              placeholder="Select resource..."
              disabled={loading}
              className="w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground/90 mb-2">
              Action <span className="text-destructive">*</span>
            </label>
            <SingleSelectCombobox
              value={action}
              onValueChange={setAction}
              options={[
                { value: '', label: 'Select action...' },
                ...actions.map((act) => ({ value: act, label: act })),
              ]}
              placeholder="Select action..."
              disabled={loading}
              className="w-full"
            />
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
          <div className="flex gap-2 justify-end flex-col sm:flex-row">
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
              disabled={loading || !resource || !action}
              className="w-full sm:w-auto flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              Create Permission
            </Button>
          </div>
        </form>
    </Modal>
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
  roles: components['schemas']['RoleResponse'][]
  loading: boolean
  onClose: () => void
}) {
  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      maxWidth="max-w-2xl"
      closeButton={!loading}
    >
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-foreground">Roles with Permission</h2>
        <p className="text-sm text-muted-foreground mt-0.5 font-mono">{permCode}</p>
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
      <div className="flex justify-end gap-2 mt-6 pt-4 border-t border-border">
        <Button
          onClick={onClose}
          disabled={loading}
        >
          Close
        </Button>
      </div>
    </Modal>
  )
}
