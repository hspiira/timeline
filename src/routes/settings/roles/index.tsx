import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { useToast } from '@/hooks/useToast'
import { timelineApi } from '@/lib/api-client'
import { getApiErrorDisplay, isAuthOrPermissionError } from '@/lib/api-utils'
import {
  Plus,
  Trash2,
  SquarePen,
  Shield,
  CheckCircle,
  Loader2,
} from 'lucide-react'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Modal } from '@/components/ui/Modal'
import { FormError } from '@/components/ui/FormField'
import { Button } from '@/components/ui/button'
import { DataTable } from '@/components/ui/DataTable'
import type { components } from '@/lib/timeline-api'

export const Route = createFileRoute('/settings/roles/')({
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
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hasNoAccess, setHasNoAccess] = useState(false)

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingRole, setEditingRole] = useState<RoleResponse | null>(null)
  const [managingPermissions, setManagingPermissions] = useState<RoleWithPermissions | null>(null)
  const [deletingRoleId, setDeletingRoleId] = useState<string | null>(null)
  const [confirmingDelete, setConfirmingDelete] = useState<{ id: string; name: string } | null>(null)
  const [includeInactive, setIncludeInactive] = useState(false)

  useEffect(() => {
    if (authState.user) {
      fetchRoles()
      fetchPermissions()
    }
  }, [authState.user, includeInactive])

  const fetchRoles = async () => {
    setLoading(true)
    setError(null)
    setHasNoAccess(false)

    try {
      const { data, error: apiError, response } = await timelineApi.roles.list({
        skip: 0,
        limit: 100,
        include_inactive: includeInactive,
      })

      if (apiError) {
        const display = getApiErrorDisplay(
          { error: apiError, status: response?.status },
          'Unable to load roles'
        )
        setHasNoAccess(isAuthOrPermissionError(display, response?.status))
        setError(display.message)
      } else {
        setRoles(data || [])
      }
    } catch (err) {
      setError('An unexpected error occurred')
      console.error('Error:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchPermissions = async () => {
    try {
      const { data, error: apiError, response } = await timelineApi.permissions.list({
        skip: 0,
        limit: 1000,
      })

      if (!apiError && data) {
        setPermissions(data)
      }
    } catch (err) {
      console.error('Error fetching permissions:', err)
    }
  }

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
      } else {
        setRoles((prev) => prev.filter((r) => r.id !== confirmingDelete.id))
        toast.success('Role deleted', `"${confirmingDelete.name}" has been deleted`)
        setConfirmingDelete(null)
      }
    } finally {
      setDeletingRoleId(null)
    }
  }

  if (!authState.user) {
    return null
  }

  // Define columns for DataTable
  const columns: ColumnDef<RoleResponse>[] = [
    {
      accessorKey: 'name',
      header: 'Name',
      cell: ({ row }) => {
        const role = row.original
        return (
          <div className="flex items-center gap-2">
            {role.is_system && (
              <span className="text-xs px-1.5 py-0.5 bg-primary/20 text-primary rounded-none font-medium">
                SYSTEM
              </span>
            )}
            <span className="font-semibold text-foreground">{role.name}</span>
          </div>
        )
      },
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
      id: 'permissions',
      header: 'Permissions',
      cell: () => (
        <span className="text-xs px-1.5 py-0.5 bg-secondary text-muted-foreground rounded-none font-mono">
          0
        </span>
      ),
    },
    {
      id: 'status',
      header: 'Status',
      cell: ({ row }) =>
        row.original.is_active ? (
          <div className="flex items-center justify-center gap-1 text-green-600 dark:text-green-400">
            <CheckCircle className="w-3 h-3" />
            <span className="text-xs">Active</span>
          </div>
        ) : (
          <span className="text-xs text-muted-foreground">Inactive</span>
        ),
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => {
        const role = row.original
        return (
          <div className="flex items-center justify-end gap-0.5">
            <Button
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
              size="sm"
              variant="ghost"
            >
              <Shield className="w-4 h-4" />
            </Button>
            <Button
              onClick={() => setEditingRole(role)}
              disabled={role.is_system || hasNoAccess}
              title={
                role.is_system
                  ? 'Cannot modify system role'
                  : hasNoAccess
                    ? 'No permission'
                    : 'Edit'
              }
              size="sm"
              variant="ghost"
            >
              <SquarePen className="w-4 h-4" />
            </Button>
            <Button
              onClick={() => handleDeleteClick(role)}
              disabled={deletingRoleId === role.id || role.is_system || hasNoAccess}
              title={
                role.is_system
                  ? 'Cannot delete system role'
                  : hasNoAccess
                    ? 'No permission'
                    : 'Delete'
              }
              size="sm"
              variant="ghost"
            >
              {deletingRoleId === role.id ? (
                <span className="w-4 h-4 animate-spin" />
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
      {error && <FormError message={error} />}

      {/* Limited Access Warning */}
      {hasNoAccess && (
        <div className="mb-3 p-3 bg-amber-50 dark:bg-amber-900/40 border border-amber-200 dark:border-amber-700 rounded-none flex gap-2">
          <div className="flex-1">
            <h3 className="font-semibold text-amber-900 dark:text-amber-100 text-sm">
              Limited Access
            </h3>
            <p className="text-sm text-amber-800 dark:text-amber-200 mt-0.5">
              You don't have permission to manage roles. You can view but cannot create or modify.
            </p>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
        <div>
          <h1 className="text-lg font-bold text-foreground">Roles</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Manage roles and their permissions</p>
        </div>
        {!hasNoAccess && (
          <Button
            onClick={() => setShowCreateModal(true)}
            variant="primary"
          >
            <Plus className="w-4 h-4" />
            Role
          </Button>
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
      <DataTable
        data={roles}
        columns={columns}
        isLoading={loading}
        isEmpty={roles.length === 0}
        compact={true}
        enablePagination={true}
        pageSize={10}
        emptyState={{
          title: 'No roles yet',
          description: hasNoAccess
            ? 'You do not have permission to view roles.'
            : 'Create your first role',
          action: !hasNoAccess ? (
            <Button onClick={() => setShowCreateModal(true)} variant="primary">
              <Plus className="w-4 h-4" />
              Role
            </Button>
          ) : undefined,
        }}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={!!confirmingDelete}
        title="Delete Role?"
        message={`Are you sure you want to delete "${confirmingDelete?.name}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        isDestructive={true}
        isLoading={deletingRoleId === confirmingDelete?.id}
        onConfirm={handleConfirmDelete}
        onCancel={() => setConfirmingDelete(null)}
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
    <Modal
      isOpen={true}
      onClose={onClose}
      title={role ? 'Edit Role' : 'Create Role'}
      maxWidth="max-w-2xl"
      closeButton={!loading}
    >
      {/* Error Alert */}
      {error && <FormError message={error} />}

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
              disabled={loading}
              className="w-full sm:w-auto"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {role ? 'Update Role' : 'Create Role'}
            </Button>
          </div>
        </form>
    </Modal>
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
    <Modal
      isOpen={true}
      onClose={onClose}
      title="Manage Permissions"
      maxWidth="max-w-3xl"
      closeButton={!loading}
    >
      <p className="text-sm text-muted-foreground mb-4">{role.name}</p>

      {/* Error Alert */}
      {error && <FormError message={error} />}

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
      <div className="flex gap-2 justify-end flex-col sm:flex-row pt-4 border-t border-border">
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
          type="button"
          onClick={handleSave}
          disabled={loading}
          className="w-full sm:w-auto"
        >
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          Save Permissions
        </Button>
      </div>
    </Modal>
  )
}
