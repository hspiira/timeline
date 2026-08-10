import type { components } from '@/lib/timeline-api'

/**
 * Centralized type definitions for the Timeline application
 * All types are derived from the OpenAPI schema for consistency
 */

// Auth & User types
export type UserResponse = components['schemas']['UserResponse']
export type UserCreateRequest = components['schemas']['UserCreateRequest']
export type UserUpdate = components['schemas']['UserUpdate']
export type RegisterRequest = components['schemas']['RegisterRequest']
export type TokenResponse = components['schemas']['TokenResponse']

// Subject types
export type SubjectResponse = components['schemas']['SubjectResponse']
export type SubjectCreateRequest = components['schemas']['SubjectCreateRequest']
export type SubjectUpdate = components['schemas']['SubjectUpdate']

// Event types
export type EventResponse = components['schemas']['EventResponse']
export type EventCreateRequest = components['schemas']['EventCreate']
export type EventListResponse = components['schemas']['EventListResponse']

// Event Schema types
export type EventSchemaResponse = components['schemas']['EventSchemaResponse']
export type EventSchemaCreateRequest = components['schemas']['EventSchemaCreateRequest']

// Tenant types
export type TenantResponse = components['schemas']['TenantResponse']
export type TenantCreateRequest = components['schemas']['TenantCreateRequest']
export type TenantCreateResponse = components['schemas']['TenantCreateResponse']

// Workflow types
export type WorkflowResponse = components['schemas']['WorkflowResponse']
export type WorkflowCreateRequest = components['schemas']['WorkflowCreateRequest']

// Flow types
export type FlowResponse = components['schemas']['FlowResponse']
export type FlowCreateRequest = components['schemas']['FlowCreateRequest']
export type FlowUpdateRequest = components['schemas']['FlowUpdateRequest']
export type FlowSubjectResponse = components['schemas']['FlowSubjectResponse']
export type FlowDocumentComplianceResponse =
  components['schemas']['FlowDocumentComplianceResponse']

// Naming template types
export type NamingTemplateResponse = components['schemas']['NamingTemplateResponse']
export type NamingTemplateCreateRequest =
  components['schemas']['NamingTemplateCreateRequest']
export type NamingTemplateUpdateRequest =
  components['schemas']['NamingTemplateUpdateRequest']

// Document types
export type DocumentListItem = components['schemas']['DocumentListItem']
export type DocumentVersionItem = components['schemas']['DocumentVersionItem']

// Email Account types
export type EmailAccountResponse = components['schemas']['EmailAccountResponse']
export type EmailAccountCreateRequest = components['schemas']['EmailAccountCreateRequest']
