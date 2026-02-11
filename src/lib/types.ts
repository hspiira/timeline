import type { components } from '@/lib/timeline-api'

/**
 * Centralized type definitions for the Timeline application
 * All types are derived from the OpenAPI schema for consistency
 */

// Auth & User types
export type UserResponse = components['schemas']['UserResponse']
export type UserCreate = components['schemas']['UserCreate']
export type UserUpdate = components['schemas']['UserUpdate']

// Subject types
export type SubjectResponse = components['schemas']['SubjectResponse']
export type SubjectCreate = components['schemas']['SubjectCreate']
export type SubjectUpdate = components['schemas']['SubjectUpdate']

// Event types
export type EventResponse = components['schemas']['EventResponse']
export type EventCreate = components['schemas']['EventCreate']
export type EventListResponse = components['schemas']['EventListResponse']

// Event Schema types
export type EventSchemaResponse = components['schemas']['EventSchemaResponse']
export type EventSchemaCreate = components['schemas']['EventSchemaCreate']

// Tenant types
export type TenantResponse = components['schemas']['TenantResponse']
export type TenantCreate = components['schemas']['TenantCreate']

// Workflow types
export type WorkflowResponse = components['schemas']['WorkflowResponse']
export type WorkflowCreate = components['schemas']['WorkflowCreate']

// Document types
export type DocumentResponse = components['schemas']['DocumentResponse']

// Email Account types
export type EmailAccountResponse = components['schemas']['EmailAccountResponse']
export type EmailAccountCreate = components['schemas']['EmailAccountCreate']

// Token types
export type Token = components['schemas']['Token']
