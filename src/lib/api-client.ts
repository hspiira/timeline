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
      return client.POST('/auth/token', {
        body: {
          username,
          password,
          tenant_code,
        },
      })
    },
    register: (data: components['schemas']['UserCreate']) =>
      client.POST('/users/register', { body: data }),
  },

  // Users
  users: {
    me: () => client.GET('/users/me'),
    update: (data: components['schemas']['UserUpdate']) =>
      client.PUT('/users/me', { body: data }),
    deactivate: () => client.DELETE('/users/me'),
    list: (params?: { skip?: number; limit?: number }) =>
      client.GET('/users/', { params: { query: params } }),
    getRoles: (userId: string) =>
      client.GET('/users/{user_id}/roles', {
        params: { path: { user_id: userId } },
      }),
    assignRole: (userId: string, data: components['schemas']['UserRoleAssign']) =>
      client.POST('/users/{user_id}/roles', {
        params: { path: { user_id: userId } },
        body: data,
      }),
    removeRole: (userId: string, roleId: string) =>
      client.DELETE('/users/{user_id}/roles/{role_id}', {
        params: { path: { user_id: userId, role_id: roleId } },
      }),
    getMyRoles: () => client.GET('/users/me/roles'),
  },

  // Tenants
  tenants: {
    list: (params?: { skip?: number; limit?: number; active_only?: boolean }) =>
      client.GET('/tenants/', { params: { query: params } }),
    get: (id: string) =>
      client.GET('/tenants/{tenant_id}', {
        params: { path: { tenant_id: id } },
      }),
    create: (data: components['schemas']['TenantCreate']) =>
      client.POST('/tenants/', { body: data }),
    update: (id: string, data: components['schemas']['TenantUpdate']) =>
      client.PUT('/tenants/{tenant_id}', {
        params: { path: { tenant_id: id } },
        body: data,
      }),
    updateStatus: (id: string, data: components['schemas']['TenantStatusUpdate']) =>
      client.PATCH('/tenants/{tenant_id}/status', {
        params: { path: { tenant_id: id } },
        body: data,
      }),
    delete: (id: string) =>
      client.DELETE('/tenants/{tenant_id}', {
        params: { path: { tenant_id: id } },
      }),
  },

  // Roles
  roles: {
    list: (params?: { skip?: number; limit?: number; include_inactive?: boolean }) =>
      client.GET('/roles/', {
        params: { query: params },
      }),
    get: (id: string) =>
      client.GET('/roles/{role_id}', {
        params: { path: { role_id: id } },
      }),
    create: (data: components['schemas']['RoleCreate']) =>
      client.POST('/roles/', { body: data }),
    update: (id: string, data: components['schemas']['RoleUpdate']) =>
      client.PUT('/roles/{role_id}', {
        params: { path: { role_id: id } },
        body: data,
      }),
    delete: (id: string) =>
      client.DELETE('/roles/{role_id}', {
        params: { path: { role_id: id } },
      }),
    assignPermissions: (roleId: string, data: components['schemas']['RolePermissionAssign']) =>
      client.POST('/roles/{role_id}/permissions', {
        params: { path: { role_id: roleId } },
        body: data,
      }),
    removePermission: (roleId: string, permissionId: string) =>
      client.DELETE('/roles/{role_id}/permissions/{permission_id}', {
        params: { path: { role_id: roleId, permission_id: permissionId } },
      }),
  },

  // Permissions
  permissions: {
    list: (params?: { skip?: number; limit?: number; resource?: string }) =>
      client.GET('/permissions/', {
        params: { query: params },
      }),
    get: (id: string) =>
      client.GET('/permissions/{permission_id}', {
        params: { path: { permission_id: id } },
      }),
    create: (data: components['schemas']['PermissionCreate']) =>
      client.POST('/permissions/', { body: data }),
    delete: (id: string) =>
      client.DELETE('/permissions/{permission_id}', {
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
      client.GET('/subjects/', {
        params: { query: params },
      }),
    get: (id: string) =>
      client.GET('/subjects/{subject_id}', {
        params: { path: { subject_id: id } },
      }),
    create: (data: components['schemas']['SubjectCreate']) =>
      client.POST('/subjects/', { body: data }),
    update: (id: string, data: components['schemas']['SubjectUpdate']) =>
      client.PUT('/subjects/{subject_id}', {
        params: { path: { subject_id: id } },
        body: data,
      }),
    delete: (id: string) =>
      client.DELETE('/subjects/{subject_id}', {
        params: { path: { subject_id: id } },
      }),
  },

  // Events
  events: {
    listAll: (params?: { event_type?: string; skip?: number; limit?: number }) =>
      client.GET('/events/', {
        params: { query: params },
      }),
    list: (
      subjectId: string,
      params?: { event_type?: string; skip?: number; limit?: number }
    ) =>
      client.GET('/events/subject/{subject_id}', {
        params: {
          path: { subject_id: subjectId },
          query: params,
        },
      }),
    get: (id: string) =>
      client.GET('/events/{event_id}', {
        params: { path: { event_id: id } },
      }),
    count: () => client.GET('/events/count'),
    create: (data: components['schemas']['EventCreate']) =>
      client.POST('/events/', { body: data }),
    verify: (subjectId: string) =>
      client.GET('/events/verify/{subject_id}', {
        params: { path: { subject_id: subjectId } },
      }),
    verifyTenant: (params?: { limit?: number }) =>
      client.GET('/events/verify/tenant/all', {
        params: { query: params },
      }),
  },

  // Event Schemas
  eventSchemas: {
    list: () => client.GET('/event-schemas/'),
    get: (id: string) =>
      client.GET('/event-schemas/{schema_id}', {
        params: { path: { schema_id: id } },
      }),
    getActive: (eventType: string) =>
      client.GET('/event-schemas/event-type/{event_type}/active', {
        params: { path: { event_type: eventType } },
      }),
    getByVersion: (eventType: string, version: number) =>
      client.GET('/event-schemas/event-type/{event_type}/version/{version}', {
        params: { path: { event_type: eventType, version } },
      }),
    create: (data: components['schemas']['EventSchemaCreate']) =>
      client.POST('/event-schemas/', { body: data }),
    update: (id: string, data: components['schemas']['EventSchemaUpdate']) =>
      client.PATCH('/event-schemas/{schema_id}', {
        params: { path: { schema_id: id } },
        body: data,
      }),
    delete: (id: string) =>
      client.DELETE('/event-schemas/{schema_id}', {
        params: { path: { schema_id: id } },
      }),
  },

  // Documents
  documents: {
    listBySubject: (subjectId: string) =>
      client.GET('/documents/subject/{subject_id}', {
        params: { path: { subject_id: subjectId } },
      }),
    listByEvent: (eventId: string) =>
      client.GET('/documents/event/{event_id}', {
        params: { path: { event_id: eventId } },
      }),
    get: (id: string) =>
      client.GET('/documents/{document_id}', {
        params: { path: { document_id: id } },
      }),
    upload: async (data: FormData) => {
      // Use native fetch for FormData instead of openapi-fetch
      // because openapi-fetch doesn't handle FormData correctly
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const url = `${baseUrl}/documents/upload`

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
      client.GET('/documents/{document_id}/download', {
        params: { path: { document_id: id } },
      }),
    delete: (id: string) =>
      client.DELETE('/documents/{document_id}', {
        params: { path: { document_id: id } },
      }),
    getVersions: (id: string) =>
      client.GET('/documents/{document_id}/versions', {
        params: { path: { document_id: id } },
      }),
    update: (id: string, data: components['schemas']['DocumentUpdate']) =>
      client.PUT('/documents/{document_id}', {
        params: { path: { document_id: id } },
        body: data,
      }),
  },

  // Workflows
  workflows: {
    list: () => client.GET('/workflows/'),
    get: (id: string) =>
      client.GET('/workflows/{workflow_id}', {
        params: { path: { workflow_id: id } },
      }),
    create: (data: components['schemas']['WorkflowCreate']) =>
      client.POST('/workflows/', { body: data }),
    update: (id: string, data: components['schemas']['WorkflowUpdate']) =>
      client.PUT('/workflows/{workflow_id}', {
        params: { path: { workflow_id: id } },
        body: data,
      }),
    delete: (id: string) =>
      client.DELETE('/workflows/{workflow_id}', {
        params: { path: { workflow_id: id } },
      }),
    getExecutions: (workflowId: string) =>
      client.GET('/workflows/{workflow_id}/executions', {
        params: { path: { workflow_id: workflowId } },
      }),
    getExecution: (executionId: string) =>
      client.GET('/workflows/executions/{execution_id}', {
        params: { path: { execution_id: executionId } },
      }),
  },

  // Email Accounts
  emailAccounts: {
    list: () => client.GET('/email-accounts/'),
    get: (id: string) =>
      client.GET('/email-accounts/{account_id}', {
        params: { path: { account_id: id } },
      }),
    create: (data: components['schemas']['EmailAccountCreate']) =>
      client.POST('/email-accounts/', { body: data }),
    update: (id: string, data: components['schemas']['EmailAccountUpdate']) =>
      client.PATCH('/email-accounts/{account_id}', {
        params: { path: { account_id: id } },
        body: data,
      }),
    delete: (id: string) =>
      client.DELETE('/email-accounts/{account_id}', {
        params: { path: { account_id: id } },
      }),
    sync: (id: string, incremental: boolean = true) =>
      client.POST('/email-accounts/{account_id}/sync', {
        params: { path: { account_id: id } },
        body: { incremental },
      }),
    syncBackground: (id: string, incremental: boolean = true) =>
      client.POST('/email-accounts/{account_id}/sync-background', {
        params: { path: { account_id: id } },
        body: { incremental },
      }),
    setupWebhook: (id: string, data: components['schemas']['WebhookSetupRequest']) =>
      client.POST('/email-accounts/{account_id}/webhook', {
        params: { path: { account_id: id } },
        body: data,
      }),
  },

  // OAuth Providers
  oauthProviders: {
    list: (params?: { include_inactive?: boolean; skip?: number; limit?: number }) =>
      client.GET('/api/oauth-providers', {
        params: { query: params },
      }),
    get: (configId: string) =>
      client.GET('/api/oauth-providers/{config_id}', {
        params: { path: { config_id: configId } },
      }),
    create: (data: components['schemas']['OAuthProviderConfigCreate']) =>
      client.POST('/api/oauth-providers', { body: data }),
    update: (configId: string, data: components['schemas']['OAuthProviderConfigUpdate']) =>
      client.PATCH('/api/oauth-providers/{config_id}', {
        params: { path: { config_id: configId } },
        body: data,
      }),
    delete: (configId: string) =>
      client.DELETE('/api/oauth-providers/{config_id}', {
        params: { path: { config_id: configId } },
      }),
    authorize: (provider: string, data: components['schemas']['OAuthAuthorizeRequest']) =>
      client.POST('/api/oauth-providers/{provider}/authorize', {
        params: { path: { provider } },
        body: data,
      }),
    rotateCredentials: (
      configId: string,
      data: components['schemas']['OAuthRotateCredentialsRequest']
    ) =>
      client.POST('/api/oauth-providers/{config_id}/rotate', {
        params: { path: { config_id: configId } },
        body: data,
      }),
    getHealth: (configId: string) =>
      client.GET('/api/oauth-providers/{config_id}/health', {
        params: { path: { config_id: configId } },
      }),
    getAudit: (configId: string, params?: { skip?: number; limit?: number }) =>
      client.GET('/api/oauth-providers/{config_id}/audit', {
        params: { path: { config_id: configId }, query: params },
      }),
    listAvailableProviders: () => client.GET('/api/oauth-providers/metadata/providers'),
  },
}
