import createClient from 'openapi-fetch'
import type { paths, components } from './timeline-api'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

let authToken: string | null = null
let tenantId: string | null = null

if (typeof window !== 'undefined') {
  tenantId = localStorage.getItem('tenant_id')
}

/**
 * Access token is stored in memory only (no localStorage) for XSS safety.
 * Refresh token is expected in an httpOnly cookie set by the backend on login.
 * On 401, the client attempts POST /api/v1/auth/refresh with credentials: 'include'.
 */
export function setAuthToken(token: string | null) {
  authToken = token
}

export function getAuthToken(): string | null {
  return authToken
}

export function setTenantId(id: string | null) {
  tenantId = id
  if (typeof window !== 'undefined') {
    if (id) {
      localStorage.setItem('tenant_id', id)
    } else {
      localStorage.removeItem('tenant_id')
    }
  }
}

export function getTenantId(): string | null {
  return tenantId
}

/** Call backend refresh endpoint; returns new access_token or null. Backend must set refresh token in httpOnly cookie. */
export async function refreshAccessToken(): Promise<string | null> {
  const url = `${BASE_URL}/api/v1/auth/refresh`
  const res = await fetch(url, { method: 'POST', credentials: 'include' })
  if (!res.ok) return null
  const data = (await res.json()) as { access_token?: string }
  return data.access_token ?? null
}

/** Redirect to login and clear token (e.g. after failed refresh). */
function redirectToLogin(opts?: { sessionExpired?: boolean }) {
  setAuthToken(null)
  if (typeof window !== 'undefined') {
    const path = window.location.pathname
    const params = new URLSearchParams()
    if (path && path !== '/login') params.set('redirect', path)
    if (opts?.sessionExpired) params.set('session_expired', '1')
    const search = params.toString() ? `?${params.toString()}` : ''
    window.location.href = `/login${search}`
  }
}

const baseFetch = typeof fetch !== 'undefined' ? fetch : globalThis.fetch
const customFetch: typeof fetch = async (input, init) => {
  const url = typeof input === 'string' ? input : input instanceof Request ? input.url : String(input)
  const isRefresh = url.includes('/api/v1/auth/refresh')
  let res = await baseFetch(input, init)
  if (res.status === 401 && !isRefresh && typeof window !== 'undefined') {
    const newToken = await refreshAccessToken()
    if (newToken) {
      setAuthToken(newToken)
      const req = input instanceof Request ? input : new Request(input, init)
      const headers = new Headers(req.headers)
      headers.set('Authorization', `Bearer ${newToken}`)
      const tid = getTenantId()
      if (tid) headers.set('X-Tenant-ID', tid)
      res = await baseFetch(req.url, { ...init, headers })
    }
    if (res.status === 401) redirectToLogin({ sessionExpired: true })
  }
  return res
}

const client = createClient<paths>({
  baseUrl: BASE_URL,
  fetch: customFetch,
})

client.use({
  onRequest({ request }) {
    const currentToken = getAuthToken()
    if (currentToken) {
      request.headers.set('Authorization', `Bearer ${currentToken}`)
    }
    const currentTenantId = getTenantId()
    if (currentTenantId) {
      request.headers.set('X-Tenant-ID', currentTenantId)
    }
    // Tenant creation: backend returns 401 without matching X-Create-Tenant-Secret (CREATE_TENANT_SECRET in backend .env).
    // Set VITE_CREATE_TENANT_SECRET in frontend .env to the same value; trim to avoid newline/space mismatches.
    if (request.method === 'POST' && request.url.includes('/api/v1/tenants')) {
      const raw = import.meta.env.VITE_CREATE_TENANT_SECRET
      const secret = typeof raw === 'string' ? raw.trim() : ''
      if (secret) {
        request.headers.set('X-Create-Tenant-Secret', secret)
      }
    }
    if (request.body && !(request.body instanceof FormData)) {
      request.headers.set('Content-Type', 'application/json')
    } else if (request.body instanceof FormData) {
      request.headers.delete('Content-Type')
    }
    return request
  },
})

export const timelineApi = {
  analytics: {
    dashboard: () => client.GET('/api/v1/analytics/dashboard'),
  },

  auditLog: {
    list: (params?: {
      skip?: number
      limit?: number
      resource_type?: string | null
      user_id?: string | null
      from_timestamp?: string | null
      to_timestamp?: string | null
    }) =>
      client.GET('/api/v1/audit-log', {
        params: { query: params },
      }),
  },

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
    setInitialPassword: (data: components['schemas']['SetInitialPasswordRequest']) =>
      client.POST('/api/v1/auth/set-initial-password', { body: data }),
  },

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

  tenants: {
    /** Backend returns current tenant only (no query params). */
    list: () => client.GET('/api/v1/tenants'),
    get: (id: string) =>
      client.GET('/api/v1/tenants/{tenant_id}', {
        params: { path: { tenant_id: id } },
      }),
    /** Create tenant (requires X-Create-Tenant-Secret when backend CREATE_TENANT_SECRET is set). admin_initial_password optional; if set, used and never returned. */
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

  subjects: {
    list: (
      params?: {
        skip?: number
        limit?: number
        subject_type?: string
      }
    ) =>
      client.GET('/api/v1/subjects', {
        params: { query: params },
      }),
    get: (id: string) =>
      client.GET('/api/v1/subjects/{subject_id}', {
        params: { path: { subject_id: id } },
      }),
    getState: (
      subjectId: string,
      params?: { as_of?: string | null; workflow_instance_id?: string | null }
    ) =>
      client.GET('/api/v1/subjects/{subject_id}/state', {
        params: { path: { subject_id: subjectId }, query: params },
      }),
    export: (subjectId: string) =>
      client.POST('/api/v1/subjects/{subject_id}/export', {
        params: { path: { subject_id: subjectId } },
      }),
    erasure: (
      subjectId: string,
      data: components['schemas']['SubjectErasureRequest']
    ) =>
      client.POST('/api/v1/subjects/{subject_id}/erasure', {
        params: { path: { subject_id: subjectId } },
        body: data,
      }),
    create: (data: components['schemas']['SubjectCreateRequest']) =>
      client.POST('/api/v1/subjects', { body: data }),
    update: (id: string, data: components['schemas']['SubjectUpdate']) =>
      client.PATCH('/api/v1/subjects/{subject_id}', {
        params: { path: { subject_id: id } },
        body: data,
      }),
    delete: (id: string) =>
      client.DELETE('/api/v1/subjects/{subject_id}', {
        params: { path: { subject_id: id } },
      }),
    /** Batch snapshot job (cron/admin). Optional limit. */
    runSnapshotJob: (params?: { limit?: number }) =>
      client.POST('/api/v1/subjects/snapshots/run', {
        params: { query: params },
      }),
    /** On-demand snapshot for one subject. */
    createSnapshot: (subjectId: string) =>
      client.POST('/api/v1/subjects/{subject_id}/snapshot', {
        params: { path: { subject_id: subjectId } },
      }),
    listRelationships: (
      subjectId: string,
      params?: {
        as_source?: boolean
        as_target?: boolean
        relationship_kind?: string | null
      }
    ) =>
      client.GET('/api/v1/subjects/{subject_id}/relationships', {
        params: { path: { subject_id: subjectId }, query: params },
      }),
    addRelationship: (
      subjectId: string,
      body: components['schemas']['SubjectRelationshipCreateRequest']
    ) =>
      client.POST('/api/v1/subjects/{subject_id}/relationships', {
        params: { path: { subject_id: subjectId } },
        body,
      }),
    removeRelationship: (
      subjectId: string,
      query: { target_subject_id: string; relationship_kind: string }
    ) =>
      client.DELETE('/api/v1/subjects/{subject_id}/relationships', {
        params: { path: { subject_id: subjectId }, query },
      }),
  },

  relationshipKinds: {
    list: () => client.GET('/api/v1/relationship-kinds'),
    get: (kindId: string) =>
      client.GET('/api/v1/relationship-kinds/{kind_id}', {
        params: { path: { kind_id: kindId } },
      }),
    create: (data: components['schemas']['RelationshipKindCreateRequest']) =>
      client.POST('/api/v1/relationship-kinds', { body: data }),
    update: (
      kindId: string,
      data: components['schemas']['RelationshipKindUpdateRequest']
    ) =>
      client.PATCH('/api/v1/relationship-kinds/{kind_id}', {
        params: { path: { kind_id: kindId } },
        body: data,
      }),
    delete: (kindId: string) =>
      client.DELETE('/api/v1/relationship-kinds/{kind_id}', {
        params: { path: { kind_id: kindId } },
      }),
  },

  documentCategories: {
    list: (params?: { skip?: number; limit?: number }) =>
      client.GET('/api/v1/document-categories', {
        params: { query: params },
      }),
    get: (id: string) =>
      client.GET('/api/v1/document-categories/{category_id}', {
        params: { path: { category_id: id } },
      }),
    create: (data: components['schemas']['DocumentCategoryCreateRequest']) =>
      client.POST('/api/v1/document-categories', { body: data }),
    update: (
      id: string,
      data: components['schemas']['DocumentCategoryUpdateRequest']
    ) =>
      client.PATCH('/api/v1/document-categories/{category_id}', {
        params: { path: { category_id: id } },
        body: data,
      }),
    delete: (id: string) =>
      client.DELETE('/api/v1/document-categories/{category_id}', {
        params: { path: { category_id: id } },
      }),
  },

  search: {
    query: (params: {
      q: string
      scope?: 'all' | 'subjects' | 'events' | 'documents'
      limit?: number
    }) =>
      client.GET('/api/v1/search', {
        params: { query: params },
      }),
  },

  retention: {
    run: () => client.POST('/api/v1/retention/run', {}),
  },

  subjectTypes: {
    list: (params?: { skip?: number; limit?: number }) =>
      client.GET('/api/v1/subject-types', {
        params: { query: params },
      }),
    get: (id: string) =>
      client.GET('/api/v1/subject-types/{subject_type_id}', {
        params: { path: { subject_type_id: id } },
      }),
    create: (data: components['schemas']['SubjectTypeCreateRequest']) =>
      client.POST('/api/v1/subject-types', { body: data }),
    update: (
      id: string,
      data: components['schemas']['SubjectTypeUpdateRequest']
    ) =>
      client.PATCH('/api/v1/subject-types/{subject_type_id}', {
        params: { path: { subject_type_id: id } },
        body: data,
      }),
    delete: (id: string) =>
      client.DELETE('/api/v1/subject-types/{subject_type_id}', {
        params: { path: { subject_type_id: id } },
      }),
  },

  events: {
    listAll: (params?: { skip?: number; limit?: number }) =>
      client.GET('/api/v1/events', {
        params: { query: params },
      }),
    list: (subjectId: string, params?: { skip?: number; limit?: number }) =>
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
    create: (data: components['schemas']['EventCreate']) =>
      client.POST('/api/v1/events', { body: data }),
    verify: (subjectId: string) =>
      client.GET('/api/v1/events/verify/{subject_id}', {
        params: { path: { subject_id: subjectId } },
      }),
    verifyTenant: () =>
      client.GET('/api/v1/events/verify/tenant/all'),
    startVerificationJob: () =>
      client.POST('/api/v1/events/verify/tenant/all/start'),
    getVerificationJobStatus: (jobId: string) =>
      client.GET('/api/v1/events/verify/tenant/jobs/{job_id}', {
        params: { path: { job_id: jobId } },
      }),
  },

  eventSchemas: {
    list: (params?: { skip?: number; limit?: number }) =>
      client.GET('/api/v1/event-schemas', { params: { query: params } }),
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

  eventTransitionRules: {
    list: (params?: { skip?: number; limit?: number }) =>
      client.GET('/api/v1/event-transition-rules', { params: { query: params } }),
    get: (ruleId: string) =>
      client.GET('/api/v1/event-transition-rules/{rule_id}', {
        params: { path: { rule_id: ruleId } },
      }),
    create: (data: components['schemas']['EventTransitionRuleCreateRequest']) =>
      client.POST('/api/v1/event-transition-rules', { body: data }),
    update: (
      ruleId: string,
      data: components['schemas']['EventTransitionRuleUpdate']
    ) =>
      client.PATCH('/api/v1/event-transition-rules/{rule_id}', {
        params: { path: { rule_id: ruleId } },
        body: data,
      }),
    delete: (ruleId: string) =>
      client.DELETE('/api/v1/event-transition-rules/{rule_id}', {
        params: { path: { rule_id: ruleId } },
      }),
  },

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
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const url = `${baseUrl}/api/v1/documents`

      try {
        const headers: Record<string, string> = {}
        const token = getAuthToken()
        const tid = getTenantId()
        if (token) headers['Authorization'] = `Bearer ${token}`
        if (tid) headers['X-Tenant-ID'] = tid

        const response = await fetch(url, {
          method: 'POST',
          headers,
          body: data,
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

  workflows: {
    list: (params?: { skip?: number; limit?: number; include_inactive?: boolean }) =>
      client.GET('/api/v1/workflows', { params: { query: params } }),
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
    documentRequirements: {
      list: (workflowId: string) =>
        client.GET('/api/v1/workflows/{workflow_id}/document-requirements', {
          params: { path: { workflow_id: workflowId } },
        }),
      create: (
        workflowId: string,
        data: components['schemas']['DocumentRequirementCreateRequest']
      ) =>
        client.POST('/api/v1/workflows/{workflow_id}/document-requirements', {
          params: { path: { workflow_id: workflowId } },
          body: data,
        }),
      delete: (requirementId: string) =>
        client.DELETE(
          '/api/v1/workflows/document-requirements/{requirement_id}',
          { params: { path: { requirement_id: requirementId } } }
        ),
    },
  },

  flows: {
    list: (params?: {
      skip?: number
      limit?: number
      workflow_id?: string | null
    }) =>
      client.GET('/api/v1/flows', { params: { query: params } }),
    get: (id: string) =>
      client.GET('/api/v1/flows/{flow_id}', {
        params: { path: { flow_id: id } },
      }),
    create: (data: components['schemas']['FlowCreateRequest']) =>
      client.POST('/api/v1/flows', { body: data }),
    update: (
      id: string,
      data: components['schemas']['FlowUpdateRequest']
    ) =>
      client.PUT('/api/v1/flows/{flow_id}', {
        params: { path: { flow_id: id } },
        body: data,
      }),
    listSubjects: (flowId: string) =>
      client.GET('/api/v1/flows/{flow_id}/subjects', {
        params: { path: { flow_id: flowId } },
      }),
    addSubjects: (
      flowId: string,
      data: components['schemas']['FlowAddSubjectsRequest']
    ) =>
      client.POST('/api/v1/flows/{flow_id}/subjects', {
        params: { path: { flow_id: flowId } },
        body: data,
      }),
    removeSubject: (flowId: string, subjectId: string) =>
      client.DELETE('/api/v1/flows/{flow_id}/subjects/{subject_id}', {
        params: { path: { flow_id: flowId, subject_id: subjectId } },
      }),
    getDocumentCompliance: (flowId: string) =>
      client.GET('/api/v1/flows/{flow_id}/document-compliance', {
        params: { path: { flow_id: flowId } },
      }),
    listEvents: (flowId: string, params?: { skip?: number; limit?: number }) =>
      client.GET('/api/v1/flows/{flow_id}/events', {
        params: { path: { flow_id: flowId }, query: params },
      }),
  },

  namingTemplates: {
    list: (params?: { skip?: number; limit?: number }) =>
      client.GET('/api/v1/naming-templates', {
        params: { query: params },
      }),
    get: (id: string) =>
      client.GET('/api/v1/naming-templates/{template_id}', {
        params: { path: { template_id: id } },
      }),
    create: (data: components['schemas']['NamingTemplateCreateRequest']) =>
      client.POST('/api/v1/naming-templates', { body: data }),
    update: (
      id: string,
      data: components['schemas']['NamingTemplateUpdateRequest']
    ) =>
      client.PUT('/api/v1/naming-templates/{template_id}', {
        params: { path: { template_id: id } },
        body: data,
      }),
    delete: (id: string) =>
      client.DELETE('/api/v1/naming-templates/{template_id}', {
        params: { path: { template_id: id } },
      }),
  },

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

  integrity: {
    listEpochs: (subjectId: string, params?: { skip?: number; limit?: number }) =>
      client.GET('/api/v1/tenants/integrity/epochs/{subject_id}', {
        params: { path: { subject_id: subjectId }, query: params },
      }),
    verifySubject: (subjectId: string) =>
      client.GET('/api/v1/tenants/integrity/verify/{subject_id}', {
        params: { path: { subject_id: subjectId } },
      }),
    verifySubjectDetail: (subjectId: string) =>
      client.GET('/api/v1/tenants/integrity/verify/{subject_id}/detail', {
        params: { path: { subject_id: subjectId } },
      }),
    getProof: (eventSeq: number) =>
      client.GET('/api/v1/tenants/integrity/proof/{event_seq}', {
        params: { path: { event_seq: eventSeq } },
      }),
    repair: {
      initiate: (data: components['schemas']['ChainRepairCreateRequest']) =>
        client.POST('/api/v1/tenants/integrity/repair', { body: data }),
      get: (repairId: string) =>
        client.GET('/api/v1/tenants/integrity/repair/{repair_id}', {
          params: { path: { repair_id: repairId } },
        }),
      approve: (repairId: string) =>
        client.POST('/api/v1/tenants/integrity/repair/{repair_id}/approve', {
          params: { path: { repair_id: repairId } },
        }),
      complete: (repairId: string) =>
        client.POST('/api/v1/tenants/integrity/repair/{repair_id}/complete', {
          params: { path: { repair_id: repairId } },
        }),
    },
  },

  connectors: {
    health: () => client.GET('/api/v1/connectors/health'),
  },

  projections: {
    list: (tenantId: string) =>
      client.GET('/api/v1/tenants/{tenant_id}/projections', {
        params: { path: { tenant_id: tenantId } },
      }),
    create: (
      tenantId: string,
      data: components['schemas']['ProjectionDefinitionCreateRequest']
    ) =>
      client.POST('/api/v1/tenants/{tenant_id}/projections', {
        params: { path: { tenant_id: tenantId } },
        body: data,
      }),
    getState: (
      tenantId: string,
      name: string,
      version: number,
      subjectId: string,
      params?: { as_of?: string | null }
    ) =>
      client.GET(
        '/api/v1/tenants/{tenant_id}/projections/{name}/{version}/subjects/{subject_id}',
        {
          params: {
            path: { tenant_id: tenantId, name, version, subject_id: subjectId },
            query: params,
          },
        }
      ),
    listStates: (
      tenantId: string,
      name: string,
      version: number,
      params?: { skip?: number; limit?: number }
    ) =>
      client.GET(
        '/api/v1/tenants/{tenant_id}/projections/{name}/{version}/states',
        {
          params: {
            path: { tenant_id: tenantId, name, version },
            query: params,
          },
        }
      ),
    deactivate: (tenantId: string, name: string, version: number) =>
      client.DELETE(
        '/api/v1/tenants/{tenant_id}/projections/{name}/{version}',
        {
          params: { path: { tenant_id: tenantId, name, version } },
        }
      ),
    rebuild: (tenantId: string, name: string, version: number) =>
      client.POST(
        '/api/v1/tenants/{tenant_id}/projections/{name}/{version}/rebuild',
        {
          params: { path: { tenant_id: tenantId, name, version } },
        }
      ),
  },

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
