import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { useToast } from '@/hooks/useToast'
import { useFetchWithError } from '@/hooks/useFetchWithError'
import { timelineApi } from '@/lib/api-client'
import {
  Loader2,
  Shield,
  Plus,
  CheckCircle,
  XCircle,
  UserPlus,
  Mail,
  User,
  Eye,
  EyeOff,
} from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { FormError } from '@/components/ui/FormField'
import { Button } from '@/components/ui/button'
import { DataTable } from '@/components/ui/DataTable'
import type { components } from '@/lib/timeline-api'

export const Route = createFileRoute('/settings/users/')({
  component: UsersPage,
})

type UserResponse = components['schemas']['UserResponse']
type RoleResponse = components['schemas']['RoleResponse']

function UsersPage() {
  const authState = useRequireAuth()
  const toast = useToast()
  const [users, setUsers] = useState<UserResponse[]>([])
  const [roles, setRoles] = useState<RoleResponse[]>([])

  const {
    data: fetchedData,
    error,
    loading,
    hasNoAccess,
    refetch,
    setError,
  } = useFetchWithError<{ users: UserResponse[]; roles: RoleResponse[] }>(
    async () => {
      const usersRes = await timelineApi.users.list({ skip: 0, limit: 100 })
      if (usersRes.error != null) {
        return { error: usersRes.error, response: usersRes.response }
      }
      const rolesRes = await timelineApi.roles.list({ skip: 0, limit: 100 })
      const rolesList = rolesRes.data || []
      return {
        data: {
          users: usersRes.data || [],
          roles: rolesList,
        },
      }
    },
    { defaultErrorMessage: 'Unable to load users', enabled: !!authState.user }
  )

  useEffect(() => {
    if (authState.user) refetch()
  }, [authState.user, refetch])

  useEffect(() => {
    if (fetchedData) {
      setUsers(fetchedData.users)
      setRoles(fetchedData.roles)
    }
  }, [fetchedData])

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [managingRolesUser, setManagingRolesUser] = useState<UserResponse | null>(null)

  if (!authState.user) {
    return null
  }

  const columns: ColumnDef<UserResponse>[] = [
    {
      accessorKey: 'username',
      header: 'Username',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-none bg-primary/10 flex items-center justify-center">
            <User className="w-4 h-4 text-primary" />
          </div>
          <div>
            <span className="font-semibold text-foreground">{row.original.username}</span>
            {row.original.id === authState.user?.id && (
              <span className="ml-2 text-xs px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded-none">
                You
              </span>
            )}
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'email',
      header: 'Email',
      cell: ({ row }) => (
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Mail className="w-3.5 h-3.5" />
          <span className="text-sm">{row.original.email}</span>
        </div>
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
        const user = row.original
        return (
          <div className="flex items-center justify-end gap-0.5">
            <Button
              onClick={() => setManagingRolesUser(user)}
              disabled={hasNoAccess}
              title={hasNoAccess ? 'No permission' : 'Manage roles'}
              size="sm"
              variant="ghost"
            >
              <Shield className="w-4 h-4" />
            </Button>
          </div>
        )
      },
    },
  ]

  return (
    <>
      {/* Create User Modal */}
      {showCreateModal && (
        <CreateUserModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={(newUser) => {
            setUsers((prev) => [...prev, newUser])
            setShowCreateModal(false)
            toast.success('User created', `${newUser.username} has been created`)
          }}
          onError={setError}
        />
      )}

      {/* Manage Roles Modal */}
      {managingRolesUser && (
        <ManageUserRolesModal
          user={managingRolesUser}
          allRoles={roles}
          onClose={() => setManagingRolesUser(null)}
          onSuccess={() => {
            setManagingRolesUser(null)
            toast.success('Roles updated', `Roles for ${managingRolesUser.username} have been updated`)
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
              You don't have permission to manage users. You can view but cannot create or modify.
            </p>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
        <div>
          <h1 className="text-lg font-bold text-foreground">Users</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Manage tenant users and their roles</p>
        </div>
        {!hasNoAccess && (
          <Button onClick={() => setShowCreateModal(true)} variant="primary">
            <Plus className="w-4 h-4" />
            User
          </Button>
        )}
      </div>

      {/* Users Table */}
      <DataTable
        data={users}
        columns={columns}
        isLoading={loading}
        isEmpty={users.length === 0}
        compact={true}
        enablePagination={true}
        pageSize={10}
        emptyState={{
          title: 'No users found',
          description: hasNoAccess
            ? 'You do not have permission to view users.'
            : 'Create your first user to get started',
          action: !hasNoAccess ? (
            <Button onClick={() => setShowCreateModal(true)} variant="primary">
              <Plus className="w-4 h-4" />
              Add User
            </Button>
          ) : undefined,
        }}
      />
    </>
  )
}

// Create User Modal
function CreateUserModal({
  onClose,
  onSuccess,
  onError,
}: {
  onClose: () => void
  onSuccess: (user: UserResponse) => void
  onError: (error: string) => void
}) {
  const authState = useRequireAuth()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tenantCode, setTenantCode] = useState<string | null>(null)

  // Fetch tenant code on mount
  useEffect(() => {
    const fetchTenantCode = async () => {
      if (!authState.user?.tenant_id) return

      try {
        const { data } = await timelineApi.tenants.get(authState.user.tenant_id)
        if (data?.code) {
          setTenantCode(data.code)
        }
      } catch (err) {
        console.error('Failed to fetch tenant:', err)
      }
    }
    fetchTenantCode()
  }, [authState.user?.tenant_id])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!username.trim()) {
      setError('Username is required')
      return
    }
    if (!email.trim()) {
      setError('Email is required')
      return
    }
    if (!password.trim()) {
      setError('Password is required')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
    if (!tenantCode) {
      setError('Unable to determine tenant. Please try again.')
      return
    }

    setLoading(true)
    try {
      const { data, error: apiError } = await timelineApi.auth.register({
        tenant_code: tenantCode,
        username: username.trim(),
        email: email.trim(),
        password: password,
      })

      if (apiError) {
        const errorMsg = (apiError as any)?.message || (apiError as any)?.detail || 'Failed to create user'
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
      title="Create User"
      maxWidth="max-w-lg"
      closeButton={!loading}
    >
      {/* Error Alert */}
      {error && <FormError message={error} />}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Username */}
        <div>
          <label className="block text-sm font-medium text-foreground/90 mb-2">
            Username <span className="text-destructive">*</span>
          </label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="johndoe"
              className="w-full pl-10 pr-3 py-2 bg-background border border-input rounded-none text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              disabled={loading}
            />
          </div>
        </div>

        {/* Email */}
        <div>
          <label className="block text-sm font-medium text-foreground/90 mb-2">
            Email <span className="text-destructive">*</span>
          </label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="john@example.com"
              className="w-full pl-10 pr-3 py-2 bg-background border border-input rounded-none text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              disabled={loading}
            />
          </div>
        </div>

        {/* Password */}
        <div>
          <label className="block text-sm font-medium text-foreground/90 mb-2">
            Password <span className="text-destructive">*</span>
          </label>
          <div className="relative">
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimum 8 characters"
              className="w-full px-3 py-2 pr-10 bg-background border border-input rounded-none text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              disabled={loading}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            User will use this password to log in
          </p>
        </div>

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
            <UserPlus className="w-4 h-4" />
            Create User
          </Button>
        </div>
      </form>
    </Modal>
  )
}

// Manage User Roles Modal
function ManageUserRolesModal({
  user,
  allRoles,
  onClose,
  onSuccess,
  onError,
}: {
  user: UserResponse
  allRoles: RoleResponse[]
  onClose: () => void
  onSuccess: () => void
  onError: (error: string) => void
}) {
  const [userRoles, setUserRoles] = useState<RoleResponse[]>([])
  const [selectedRoles, setSelectedRoles] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchUserRoles()
  }, [user.id])

  const fetchUserRoles = async () => {
    setLoading(true)
    try {
      const { data, error: apiError } = await timelineApi.users.getRoles(user.id)
      if (apiError) {
        setError((apiError as any)?.message || 'Failed to load user roles')
      } else if (data) {
        setUserRoles(data)
        setSelectedRoles(new Set(data.map((r) => r.id)))
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)

    try {
      const currentRoleIds = userRoles.map((r) => r.id)
      const newRoleIds = Array.from(selectedRoles)

      // Roles to assign
      const toAssign = newRoleIds.filter((id) => !currentRoleIds.includes(id))
      // Roles to remove
      const toRemove = currentRoleIds.filter((id) => !newRoleIds.includes(id))

      // Assign new roles
      for (const roleId of toAssign) {
        const { error: apiError } = await timelineApi.users.assignRole(user.id, roleId)
        if (apiError) {
          const errorMsg = (apiError as any)?.message || 'Failed to assign role'
          setError(errorMsg)
          onError(errorMsg)
          return
        }
      }

      // Remove roles
      for (const roleId of toRemove) {
        const { error: apiError } = await timelineApi.users.removeRole(user.id, roleId)
        if (apiError) {
          const errorMsg = (apiError as any)?.message || 'Failed to remove role'
          setError(errorMsg)
          onError(errorMsg)
          return
        }
      }

      onSuccess()
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title="Manage User Roles"
      maxWidth="max-w-lg"
      closeButton={!saving}
    >
      <div className="flex items-center gap-2 mb-4 p-3 bg-muted rounded-none">
        <div className="w-8 h-8 rounded-none bg-primary/10 flex items-center justify-center">
          <User className="w-4 h-4 text-primary" />
        </div>
        <div>
          <span className="font-medium text-foreground">{user.username}</span>
          <p className="text-xs text-muted-foreground">{user.email}</p>
        </div>
      </div>

      {/* Error Alert */}
      {error && <FormError message={error} />}

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <>
          {/* Roles List */}
          <div className="space-y-2 max-h-64 overflow-y-auto mb-4">
            {allRoles.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">No roles available</p>
            ) : (
              allRoles.map((role) => (
                <label
                  key={role.id}
                  className="flex items-center gap-2 p-2 hover:bg-muted rounded-none cursor-pointer transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={selectedRoles.has(role.id)}
                    onChange={(e) => {
                      const newSelected = new Set(selectedRoles)
                      if (e.target.checked) {
                        newSelected.add(role.id)
                      } else {
                        newSelected.delete(role.id)
                      }
                      setSelectedRoles(newSelected)
                    }}
                    disabled={saving}
                    className="w-4 h-4 rounded-none border-input"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-foreground">{role.name}</span>
                      {role.is_system && (
                        <span className="text-xs px-1.5 py-0.5 bg-primary/20 text-primary rounded-none font-medium">
                          SYSTEM
                        </span>
                      )}
                    </div>
                    {role.description && (
                      <p className="text-xs text-muted-foreground">{role.description}</p>
                    )}
                  </div>
                </label>
              ))
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2 justify-end flex-col sm:flex-row pt-4 border-t border-border">
            <Button
              type="button"
              onClick={onClose}
              disabled={saving}
              variant="outline"
              className="w-full sm:w-auto"
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="w-full sm:w-auto"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              Save Roles
            </Button>
          </div>
        </>
      )}
    </Modal>
  )
}
