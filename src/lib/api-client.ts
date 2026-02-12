import createClient from 'openapi-fetch'
import type { paths, components } from './timeline-api'

// Create API client
const client = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
})

// Auth token management
let authToken: string | null = null

if (typeof window !== 'undefined') {
  authToken = localStorage.getItem('auth_token')
}

export function setAuthToken(token: string | null) {
  authToken = token
  if (typeof window !== 'undefined') {
    if (token) {
      localStorage.setItem('auth_token', token)
    } else {
      localStorage.removeItem('auth_token')
    }
  }
}

export function getAuthToken(): string | null {
  return authToken
}

// Add auth and content-type interceptor
client.use({
  onRequest({ request }) {
    // Always read current token at request time (not cached module-level authToken)
    const currentToken = getAuthToken()
    if (currentToken) {
      request.headers.set('Authorization', `Bearer ${currentToken}`)
    }
    // Set Content-Type for non-FormData requests
    // For FormData, let the browser set Content-Type with proper boundary
    if (request.body && !(request.body instanceof FormData)) {
      request.headers.set('Content-Type', 'application/json')
    } else if (request.body instanceof FormData) {
      // Explicitly do NOT set Content-Type for FormData
      // The browser will set it automatically with the correct boundary
      request.headers.delete('Content-Type')
    }
    return request
  },
})

// Type-safe Timeline API
export const timelineApi = {
  // Auth
  auth: {
    login: async (username: string, password: string, tenant_code: string) => {
      return client.POST('/api/v1/auth/login', {
        body: {
          username,
          password,
          tenant_code,
        },
      })
    },
    register: (data: components['schemas']['RegisterRequest']) =>
      client.POST('/api/v1/auth/register', { body: data }),
  },

  // Users
  users: {
    me: () => client.GET('/api/v1/auth/me'),
    update: (data: components['schemas']['UserUpdate']) =>
      client.PUT('/api/v1/auth/me', { body: data }),
    deactivate: () => client.DELETE('/api/v1/auth/me'),
    list: (params?: { skip?: number; limit?: number }) =>
      client.GET('/api/v1/users', { params: { query: params } }),
    getRoles: (userId: string) =>
      client.GET('/api/v1/users/{user_id}/roles', {
        params: { path: { user_id: userId } },
      }),
    assignRole: (userId: string, roleId: string) =>
      client.POST('/api/v1/users/{user_id}/roles/{role_id}', {
        params: { path: { user_id: userId, role_id: roleId } },
      }),
    removeRole: (userId: string, roleId: string) =>
      client.DELETE('/api/v1/users/{user_id}/roles/{role_id}', {
        params: { path: { user_id: userId, role_id: roleId } },
      }),
    getMyRoles: () => client.GET('/api/v1/users/me/roles'),
  },

  // Tenants
  tenants: {
    list: (params?: { skip?: number; limit?: number; active_only?: boolean }) =>
      client.GET('/api/v1/tenants', { params: { query: params } }),
    get: (id: string) =>
      client.GET('/api/v1/tenants/{tenant_id}', {
        params: { path: { tenant_id: id } },
      }),
    create: (data: components['schemas']['TenantCreateRequest']) =>
      client.POST('/api/v1/tenants', { body: data }),
    update: (id: string, data: components['schemas']['TenantUpdate']) =>
      client.PUT('/api/v1/tenants/{tenant_id}', {
        params: { path: { tenant_id: id } },
        body: data,
      }),
    updateStatus: (id: string, data: components['schemas']['TenantStatusUpdate']) =>
      client.PATCH('/api/v1/tenants/{tenant_id}/status', {
        params: { path: { tenant_id: id } },
        body: data,
      }),
    delete: (id: string) =>
      client.DELETE('/api/v1/tenants/{tenant_id}', {
        params: { path: { tenant_id: id } },
      }),
  },

  // Roles
  roles: {
    list: (params?: { skip?: number; limit?: number; include_inactive?: boolean }) =>
      client.GET('/api/v1/roles', {
        params: { query: params },
      }),
    get: (id: string) =>
      client.GET('/api/v1/roles/{role_id}', {
        params: { path: { role_id: id } },
      }),
    create: (data: components['schemas']['RoleCreateRequest']) =>
      client.POST('/api/v1/roles', { body: data }),
    update: (id: string, data: components['schemas']['RoleUpdate']) =>
      client.PUT('/api/v1/roles/{role_id}', {
        params: { path: { role_id: id } },
        body: data,
      }),
    delete: (id: string) =>
      client.DELETE('/api/v1/roles/{role_id}', {
        params: { path: { role_id: id } },
      }),
    assignPermissions: (roleId: string, data: components['schemas']['RolePermissionAssign']) =>
      client.POST('/api/v1/roles/{role_id}/permissions', {
        params: { path: { role_id: roleId } },
        body: data,
      }),
    removePermission: (roleId: string, permissionId: string) =>
      client.DELETE('/api/v1/roles/{role_id}/permissions/{permission_id}', {
        params: { path: { role_id: roleId, permission_id: permissionId } },
      }),
  },

  // Permissions
  permissions: {
    list: (params?: { skip?: number; limit?: number; resource?: string }) =>
      client.GET('/api/v1/permissions', {
        params: { query: params },
      }),
    get: (id: string) =>
      client.GET('/api/v1/permissions/{permission_id}', {
        params: { path: { permission_id: id } },
      }),
    create: (data: components['schemas']['PermissionCreateRequest']) =>
      client.POST('/api/v1/permissions', { body: data }),
    delete: (id: string) =>
      client.DELETE('/api/v1/permissions/{permission_id}', {
        params: { path: { permission_id: id } },
      }),
  },

  // Subjects
  subjects: {
    list: (
      params?: {
        skip?: number
        limit?: number
        subject_type?: string
        q?: string
      }
    ) =>
      client.GET('/api/v1/subjects', {
        params: { query: params },
      }),
    get: (id: string) =>
      client.GET('/api/v1/subjects/{subject_id}', {
        params: { path: { subject_id: id } },
      }),
    create: (data: components['schemas']['SubjectCreateRequest']) =>
      client.POST('/api/v1/subjects', { body: data }),
    update: (id: string, data: components['schemas']['SubjectUpdate']) =>
      client.PUT('/api/v1/subjects/{subject_id}', {
        params: { path: { subject_id: id } },
        body: data,
      }),
    delete: (id: string) =>
      client.DELETE('/api/v1/subjects/{subject_id}', {
        params: { path: { subject_id: id } },
      }),
  },

  // Events
  events: {
    listAll: (params?: { event_type?: string; skip?: number; limit?: number }) =>
      client.GET('/api/v1/events', {
        params: { query: params },
      }),
    list: (
      subjectId: string,
      params?: { event_type?: string; skip?: number; limit?: number }
    ) =>
      client.GET('/api/v1/events', {
        params: {
          query: { subject_id: subjectId, ...params },
        },
      }),
    get: (id: string) =>
      client.GET('/api/v1/events/{event_id}', {
        params: { path: { event_id: id } },
      }),
    count: () => client.GET('/api/v1/events/count'),
    create: (data: components['schemas']['EventCreateRequest']) =>
      client.POST('/api/v1/events', { body: data }),
    verify: (subjectId: string) =>
      client.GET('/api/v1/events/verify/{subject_id}', {
        params: { path: { subject_id: subjectId } },
      }),
    verifyTenant: () =>
      client.GET('/api/v1/events/verify/tenant/all'),
  },

  // Event Schemas
  eventSchemas: {
    listByEventType: (eventType: string) =>
      client.GET('/api/v1/event-schemas/event-type/{event_type}', {
        params: { path: { event_type: eventType } },
      }),
    get: (id: string) =>
      client.GET('/api/v1/event-schemas/{schema_id}', {
        params: { path: { schema_id: id } },
      }),
    getActive: (eventType: string) =>
      client.GET('/api/v1/event-schemas/event-type/{event_type}/active', {
        params: { path: { event_type: eventType } },
      }),
    getByVersion: (eventType: string, version: number) =>
      client.GET('/api/v1/event-schemas/event-type/{event_type}/version/{version}', {
        params: { path: { event_type: eventType, version } },
      }),
    create: (data: components['schemas']['EventSchemaCreateRequest']) =>
      client.POST('/api/v1/event-schemas', { body: data }),
    update: (id: string, data: components['schemas']['EventSchemaUpdate']) =>
      client.PATCH('/api/v1/event-schemas/{schema_id}', {
        params: { path: { schema_id: id } },
        body: data,
      }),
    delete: (id: string) =>
      client.DELETE('/api/v1/event-schemas/{schema_id}', {
        params: { path: { schema_id: id } },
      }),
  },

  // Documents
  documents: {
    listBySubject: (subjectId: string) =>
      client.GET('/api/v1/documents', {
        params: { query: { subject_id: subjectId } },
      }),
    listByEvent: (eventId: string) =>
      client.GET('/api/v1/documents/event/{event_id}', {
        params: { path: { event_id: eventId } },
      }),
    get: (id: string) =>
      client.GET('/api/v1/documents/{document_id}', {
        params: { path: { document_id: id } },
      }),
    upload: async (data: FormData) => {
      // Use native fetch for FormData instead of openapi-fetch
      // because openapi-fetch doesn't handle FormData correctly
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const url = `${baseUrl}/api/v1/documents`

      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Authorization': authToken ? `Bearer ${authToken}` : '',
          },
          body: data,
          // Explicitly do NOT set Content-Type - let browser set it with boundary
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => null)
          return { data: null, error: errorData || { message: `Upload failed with status ${response.status}` } }
        }

        const responseData = await response.json()
        return { data: responseData, error: null }
      } catch (err) {
        const error = err instanceof Error ? err.message : String(err)
        return { data: null, error: { message: error } }
      }
    },
    download: (id: string) =>
      client.GET('/api/v1/documents/{document_id}/download-url', {
        params: { path: { document_id: id } },
      }),
    delete: (id: string) =>
      client.DELETE('/api/v1/documents/{document_id}', {
        params: { path: { document_id: id } },
      }),
    getVersions: (id: string) =>
      client.GET('/api/v1/documents/{document_id}/versions', {
        params: { path: { document_id: id } },
      }),
    update: (id: string, data: components['schemas']['DocumentUpdate']) =>
      client.PUT('/api/v1/documents/{document_id}', {
        params: { path: { document_id: id } },
        body: data,
      }),
  },

  // Workflows
  workflows: {
    list: () => client.GET('/api/v1/workflows'),
    get: (id: string) =>
      client.GET('/api/v1/workflows/{workflow_id}', {
        params: { path: { workflow_id: id } },
      }),
    create: (data: components['schemas']['WorkflowCreateRequest']) =>
      client.POST('/api/v1/workflows', { body: data }),
    update: (id: string, data: components['schemas']['WorkflowUpdate']) =>
      client.PUT('/api/v1/workflows/{workflow_id}', {
        params: { path: { workflow_id: id } },
        body: data,
      }),
    delete: (id: string) =>
      client.DELETE('/api/v1/workflows/{workflow_id}', {
        params: { path: { workflow_id: id } },
      }),
    getExecutions: (workflowId: string) =>
      client.GET('/api/v1/workflows/{workflow_id}/executions', {
        params: { path: { workflow_id: workflowId } },
      }),
    getExecution: (executionId: string) =>
      client.GET('/api/v1/workflows/executions/{execution_id}', {
        params: { path: { execution_id: executionId } },
      }),
  },

  // Email Accounts
  emailAccounts: {
    list: () => client.GET('/api/v1/email-accounts'),
    get: (id: string) =>
      client.GET('/api/v1/email-accounts/{account_id}', {
        params: { path: { account_id: id } },
      }),
    create: (data: components['schemas']['EmailAccountCreateRequest']) =>
      client.POST('/api/v1/email-accounts', { body: data }),
    update: (id: string, data: components['schemas']['EmailAccountUpdate']) =>
      client.PATCH('/api/v1/email-accounts/{account_id}', {
        params: { path: { account_id: id } },
        body: data,
      }),
    delete: (id: string) =>
      client.DELETE('/api/v1/email-accounts/{account_id}', {
        params: { path: { account_id: id } },
      }),
    sync: (id: string) =>
      client.POST('/api/v1/email-accounts/{account_id}/sync', {
        params: { path: { account_id: id } },
      }),
    syncBackground: (id: string) =>
      client.POST('/api/v1/email-accounts/{account_id}/sync-background', {
        params: { path: { account_id: id } },
      }),
    getSyncStatus: (id: string) =>
      client.GET('/api/v1/email-accounts/{account_id}/sync-status', {
        params: { path: { account_id: id } },
      }),
  },

  // OAuth Providers
  oauthProviders: {
    list: (params?: { include_inactive?: boolean; skip?: number; limit?: number }) =>
      client.GET('/api/v1/oauth-providers', {
        params: { query: params },
      }),
    get: (configId: string) =>
      client.GET('/api/v1/oauth-providers/{config_id}', {
        params: { path: { config_id: configId } },
      }),
    create: (data: components['schemas']['OAuthConfigCreateRequest']) =>
      client.POST('/api/v1/oauth-providers', { body: data }),
    update: (configId: string, data: components['schemas']['OAuthConfigUpdate']) =>
      client.PATCH('/api/v1/oauth-providers/{config_id}', {
        params: { path: { config_id: configId } },
        body: data,
      }),
    delete: (configId: string) =>
      client.DELETE('/api/v1/oauth-providers/{config_id}', {
        params: { path: { config_id: configId } },
      }),
    authorize: (provider: string) =>
      client.POST('/api/v1/oauth-providers/{provider}/authorize', {
        params: { path: { provider } },
      }),
    rotateCredentials: (
      configId: string,
      data: components['schemas']['OAuthConfigRotateRequest']
    ) =>
      client.POST('/api/v1/oauth-providers/{config_id}/rotate', {
        params: { path: { config_id: configId } },
        body: data,
      }),
    getHealth: (configId: string) =>
      client.GET('/api/v1/oauth-providers/{config_id}/health', {
        params: { path: { config_id: configId } },
      }),
    getAudit: (configId: string) =>
      client.GET('/api/v1/oauth-providers/{config_id}/audit', {
        params: { path: { config_id: configId } },
      }),
    listAvailableProviders: () => client.GET('/api/v1/oauth-providers/metadata/providers'),
  },
}
