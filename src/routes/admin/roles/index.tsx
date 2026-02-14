import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { useToast } from '@/hooks/useToast'
import { useFetchWithError } from '@/hooks/useFetchWithError'
import { timelineApi } from '@/lib/api-client'
import {
  AlertCircle,
  Loader2,
  Plus,
  Trash2,
  Edit2,
  Shield,
  CheckCircle,
  X,
} from 'lucide-react'
import { ConfirmModal } from '@/components/ui/ConfirmModal'
import type { components } from '@/lib/timeline-api'

export const Route = createFileRoute('/admin/roles/')({
  component: RolesPage,
})

type RoleResponse = components['schemas']['RoleResponse']
type PermissionResponse = components['schemas']['PermissionResponse']

// RoleWithPermissions doesn't exist in the API schema — define locally
type RoleWithPermissions = RoleResponse & {
  permissions?: PermissionResponse[]
}

function RolesPage() {
  const authState = useRequireAuth()
  const toast = useToast()
  const [roles, setRoles] = useState<RoleResponse[]>([])
  const [permissions, setPermissions] = useState<PermissionResponse[]>([])
  const [includeInactive, setIncludeInactive] = useState(false)

  const {
    data: fetchedData,
    error,
    loading,
    hasNoAccess,
    refetch,
    setError,
  } = useFetchWithError<{ roles: RoleResponse[]; permissions: PermissionResponse[] }>(
    async () => {
      const rolesRes = await timelineApi.roles.list({
        skip: 0,
        limit: 100,
        include_inactive: includeInactive,
      })
      if (rolesRes.error != null) {
        return { error: rolesRes.error, response: rolesRes.response }
      }
      const permRes = await timelineApi.permissions.list({ skip: 0, limit: 1000 })
      const permissionsList = !permRes.error && permRes.data ? permRes.data : []
      return { data: { roles: rolesRes.data || [], permissions: permissionsList } }
    },
    { defaultErrorMessage: 'Unable to load roles', enabled: !!authState.user }
  )

  useEffect(() => {
    if (authState.user) refetch()
  }, [authState.user, includeInactive, refetch])

  useEffect(() => {
    if (fetchedData) {
      setRoles(fetchedData.roles)
      setPermissions(fetchedData.permissions)
    }
  }, [fetchedData])

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingRole, setEditingRole] = useState<RoleResponse | null>(null)
  const [managingPermissions, setManagingPermissions] = useState<RoleWithPermissions | null>(null)
  const [deletingRoleId, setDeletingRoleId] = useState<string | null>(null)
  const [confirmingDelete, setConfirmingDelete] = useState<{ id: string; name: string } | null>(null)

  const handleDeleteClick = (role: RoleResponse) => {
    if (hasNoAccess) {
      toast.error('Permission denied', 'You do not have permission to delete roles')
      return
    }

    if (role.is_system) {
      toast.error('Cannot delete', 'System roles cannot be deleted')
      return
    }

    setConfirmingDelete({ id: role.id, name: role.name })
  }

  const handleConfirmDelete = async () => {
    if (!confirmingDelete) return

    setDeletingRoleId(confirmingDelete.id)
    try {
      const { error: apiError } = await timelineApi.roles.delete(confirmingDelete.id)

      if (apiError) {
        const errorMsg = // @ts-ignore
          apiError?.message || 'Failed to delete role'
        setError(errorMsg)
        toast.error('Failed to delete', errorMsg)
        throw new Error(errorMsg)
      }

      setRoles((prev) => prev.filter((r) => r.id !== confirmingDelete.id))
      toast.success('Role deleted', `"${confirmingDelete.name}" has been deleted`)
    } catch (err) {
      throw err
    } finally {
      setDeletingRoleId(null)
    }
  }

  if (!authState.user) {
    return null
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>Loading roles...</span>
        </div>
      </div>
    )
  }

  return (
    <>
      {/* Create Modal */}
      {showCreateModal && (
        <RoleFormModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={(newRole) => {
            setRoles((prev) => [...prev, newRole])
            setShowCreateModal(false)
            setError(null)
          }}
          onError={setError}
          allPermissions={permissions}
        />
      )}

      {/* Edit Modal */}
      {editingRole && (
        <RoleFormModal
          role={editingRole}
          onClose={() => setEditingRole(null)}
          onSuccess={(updatedRole) => {
            setRoles((prev) =>
              prev.map((r) => (r.id === updatedRole.id ? updatedRole : r))
            )
            setEditingRole(null)
            setError(null)
          }}
          onError={setError}
          allPermissions={permissions}
        />
      )}

      {/* Manage Permissions Modal */}
      {managingPermissions && (
        <ManageRolePermissionsModal
          role={managingPermissions}
          allPermissions={permissions}
          onClose={() => setManagingPermissions(null)}
          onSuccess={(updatedRole) => {
            setRoles((prev) =>
              prev.map((r) => (r.id === updatedRole.id ? updatedRole : r))
            )
            setManagingPermissions(null)
            setError(null)
          }}
          onError={setError}
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
              You don't have permission to manage roles. You can view but cannot create or modify.
            </p>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <h1 className="text-lg font-bold text-foreground">Roles</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Manage roles and their permissions</p>
        </div>
        {!hasNoAccess && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded-none font-medium hover:bg-primary/90 transition-colors"
          >
            <Plus className="w-3 h-3" />
            Create Role
          </button>
        )}
      </div>

      {/* Filter */}
      <div className="mb-3 p-2.5 bg-card/80 backdrop-blur-sm rounded-none border border-border/50 flex items-center gap-2">
        <input
          type="checkbox"
          id="includeInactive"
          checked={includeInactive}
          onChange={(e) => setIncludeInactive(e.target.checked)}
          className="w-4 h-4 rounded-none border-input"
        />
        <label htmlFor="includeInactive" className="text-sm text-foreground cursor-pointer">
          Show inactive roles
        </label>
      </div>

      {/* Roles Table */}
      {roles.length === 0 ? (
        <div className="text-center py-8 bg-card/80 rounded-none border border-border/50 p-4">
          <h3 className="text-sm font-semibold text-foreground mb-1">No roles yet</h3>
          <p className="text-sm text-muted-foreground mb-3">
            {hasNoAccess ? 'You do not have permission to view roles.' : 'Create your first role'}
          </p>
          {!hasNoAccess && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded-none font-medium hover:bg-primary/90 transition-colors"
            >
              <Plus className="w-3 h-3" />
              Create Role
            </button>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto bg-card/80 rounded-none border border-border/50">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 px-2.5 font-medium text-muted-foreground text-sm">
                  NAME
                </th>
                <th className="text-left py-2 px-2.5 font-medium text-muted-foreground text-sm">
                  DESCRIPTION
                </th>
                <th className="text-center py-2 px-2.5 font-medium text-muted-foreground text-sm">
                  PERMISSIONS
                </th>
                <th className="text-center py-2 px-2.5 font-medium text-muted-foreground text-sm">
                  STATUS
                </th>
                <th className="text-right py-2 px-2.5 font-medium text-muted-foreground text-sm">
                  ACTIONS
                </th>
              </tr>
            </thead>
            <tbody>
              {roles.map((role) => (
                <tr
                  key={role.id}
                  className="border-b border-border hover:bg-muted/50 transition-colors"
                >
                  <td className="py-2 px-2.5">
                    <div>
                      <div className="flex items-center gap-2">
                        {role.is_system && (
                          <span className="text-xs px-1.5 py-0.5 bg-primary/20 text-primary rounded-none font-medium">
                            SYSTEM
                          </span>
                        )}
                        <span className="font-semibold text-foreground">{role.name}</span>
                      </div>
                    </div>
                  </td>
                  <td className="py-2 px-2.5 text-muted-foreground text-sm max-w-sm truncate">
                    {role.description || '-'}
                  </td>
                  <td className="py-2 px-2.5 text-center">
                    <span className="text-xs px-1.5 py-0.5 bg-secondary text-muted-foreground rounded-none font-mono">
                      0
                    </span>
                  </td>
                  <td className="py-2 px-2.5 text-center">
                    {role.is_active ? (
                      <div className="flex items-center justify-center gap-1 text-green-600 dark:text-green-400">
                        <CheckCircle className="w-3 h-3" />
                        <span className="text-xs">Active</span>
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground">Inactive</span>
                    )}
                  </td>
                  <td className="py-2 px-2.5 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => {
                          setManagingPermissions(role as RoleWithPermissions)
                        }}
                        disabled={role.is_system || hasNoAccess}
                        title={
                          role.is_system
                            ? 'Cannot modify system role'
                            : hasNoAccess
                              ? 'No permission'
                              : 'Manage permissions'
                        }
                        className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Shield className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setEditingRole(role)}
                        disabled={role.is_system || hasNoAccess}
                        title={
                          role.is_system
                            ? 'Cannot modify system role'
                            : hasNoAccess
                              ? 'No permission'
                              : 'Edit'
                        }
                        className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteClick(role)}
                        disabled={deletingRoleId === role.id || role.is_system || hasNoAccess}
                        title={
                          role.is_system
                            ? 'Cannot delete system role'
                            : hasNoAccess
                              ? 'No permission'
                              : 'Delete'
                        }
                        className="p-1 text-muted-foreground hover:text-red-600 dark:hover:text-red-400 hover:bg-muted rounded-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {deletingRoleId === role.id ? (
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
      <ConfirmModal
        isOpen={!!confirmingDelete}
        onClose={() => setConfirmingDelete(null)}
        title="Delete Role?"
        message={`Are you sure you want to delete "${confirmingDelete?.name}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        isDestructive={true}
        onConfirm={handleConfirmDelete}
      />
    </>
  )
}

// Role Form Modal Component
function RoleFormModal({
  role,
  onClose,
  onSuccess,
  onError,
}: {
  role?: RoleResponse
  onClose: () => void
  onSuccess: (role: RoleResponse) => void
  onError: (error: string) => void
  allPermissions: PermissionResponse[]
}) {
  const [name, setName] = useState(role?.name || '')
  const [description, setDescription] = useState(role?.description || '')
  const [code, setCode] = useState(role?.code || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!name.trim()) {
      setError('Role name is required')
      return
    }

    if (!role && !code.trim()) {
      setError('Role code is required')
      return
    }

    setLoading(true)
    try {
      if (role) {
        const { data, error: apiError } = await timelineApi.roles.update(role.id, {
          name: name.trim(),
          description: description.trim() || null,
          is_active: role.is_active,
        })

        if (apiError) {
          const errorMsg = // @ts-ignore
            apiError?.message || 'Failed to update role'
          setError(errorMsg)
          onError(errorMsg)
        } else if (data) {
          onSuccess(data)
        }
      } else {
        const { data, error: apiError } = await timelineApi.roles.create({
          code: code.trim(),
          name: name.trim(),
          description: description.trim() || null,
        })

        if (apiError) {
          const errorMsg = // @ts-ignore
            apiError?.message || 'Failed to create role'
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

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-background border border-border rounded-none max-w-2xl w-full max-h-[90vh] overflow-auto p-6 shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-foreground">
            {role ? 'Edit Role' : 'Create Role'}
          </h2>
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
          {!role && (
            <div>
              <label className="block text-sm font-medium text-foreground/90 mb-2">
                Code <span className="text-destructive">*</span>
              </label>
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="e.g., editor, viewer"
                className="w-full px-3 py-2 bg-background border border-input rounded-none text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
                disabled={loading}
              />
              <p className="text-xs text-muted-foreground mt-1">
                Unique identifier for this role. Cannot be changed after creation.
              </p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-foreground/90 mb-2">
              Name <span className="text-destructive">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Content Editor"
              className="w-full px-3 py-2 bg-background border border-input rounded-none text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              disabled={loading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground/90 mb-2">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this role can do..."
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
              disabled={loading}
              className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-none hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {role ? 'Update Role' : 'Create Role'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Manage Role Permissions Modal
function ManageRolePermissionsModal({
  role,
  allPermissions,
  onClose,
  onSuccess,
  onError,
}: {
  role: RoleWithPermissions
  allPermissions: PermissionResponse[]
  onClose: () => void
  onSuccess: (role: RoleWithPermissions) => void
  onError: (error: string) => void
}) {
  const [selectedPermissions, setSelectedPermissions] = useState<Set<string>>(
    new Set(role.permissions?.map((p: PermissionResponse) => p.id) || [])
  )
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Group permissions by resource
  const permissionsByResource = allPermissions.reduce(
    (acc, perm) => {
      if (!acc[perm.resource]) {
        acc[perm.resource] = []
      }
      acc[perm.resource].push(perm)
      return acc
    },
    {} as Record<string, PermissionResponse[]>
  )

  const handleSave = async () => {
    setError(null)
    setLoading(true)

    try {
      const existingIds = role.permissions?.map((p: PermissionResponse) => p.id) || []
      const toAssign = Array.from(selectedPermissions).filter(
        (id: string) => !existingIds.includes(id)
      )

      const toRemove = existingIds.filter((id: string) => !selectedPermissions.has(id))

      // Assign new permissions one at a time (API takes single permission_id)
      for (const permId of toAssign) {
        const { error: apiError } = await timelineApi.roles.assignPermissions(role.id, {
          permission_id: permId,
        })

        if (apiError) {
          const errorMsg = // @ts-ignore
            apiError?.message || 'Failed to assign permissions'
          setError(errorMsg)
          onError(errorMsg)
          return
        }
      }

      // Remove permissions
      for (const permId of toRemove) {
        const { error: apiError } = await timelineApi.roles.removePermission(role.id, permId)

        if (apiError) {
          const errorMsg = // @ts-ignore
            apiError?.message || 'Failed to remove permission'
          setError(errorMsg)
          onError(errorMsg)
          return
        }
      }

      // Fetch updated role
      const { data, error: fetchError } = await timelineApi.roles.get(role.id)

      if (fetchError) {
        const errorMsg = // @ts-ignore
          fetchError?.message || 'Failed to load updated role'
        setError(errorMsg)
        onError(errorMsg)
      } else if (data) {
        onSuccess(data as RoleWithPermissions)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-background border border-border rounded-none max-w-3xl w-full max-h-[90vh] overflow-auto p-6 shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold text-foreground">Manage Permissions</h2>
            <p className="text-sm text-muted-foreground mt-0.5">{role.name}</p>
          </div>
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

        {/* Permissions Grid */}
        <div className="space-y-4 mb-6">
          {Object.entries(permissionsByResource).map(([resource, perms]) => (
            <div key={resource}>
              <h3 className="text-sm font-semibold text-foreground mb-2 capitalize">{resource}</h3>
              <div className="grid grid-cols-2 gap-2">
                {perms.map((perm) => (
                  <label
                    key={perm.id}
                    className="flex items-center gap-2 p-2 hover:bg-muted rounded-none cursor-pointer transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={selectedPermissions.has(perm.id)}
                      onChange={(e) => {
                        const newSelected = new Set(selectedPermissions)
                        if (e.target.checked) {
                          newSelected.add(perm.id)
                        } else {
                          newSelected.delete(perm.id)
                        }
                        setSelectedPermissions(newSelected)
                      }}
                      disabled={loading}
                      className="w-4 h-4 rounded-none border-input"
                    />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-foreground">{perm.code}</p>
                      {perm.description && (
                        <p className="text-xs text-muted-foreground">{perm.description}</p>
                      )}
                    </div>
                  </label>
                ))}
              </div>
            </div>
          ))}
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
            type="button"
            onClick={handleSave}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-none hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            Save Permissions
          </button>
        </div>
      </div>
    </div>
  )
}
