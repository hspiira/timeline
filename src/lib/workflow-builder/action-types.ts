import type { LucideIcon } from 'lucide-react'
import { Link2, Mail, UserCog, Zap } from 'lucide-react'

/** Single source of truth for workflow action types (create_event, send_email, update_subject, create_relationship). */

export const WORKFLOW_ACTION_TYPES = [
  { value: 'create_event', label: 'Create Event', icon: Zap },
  { value: 'send_email', label: 'Send Email', icon: Mail },
  { value: 'update_subject', label: 'Update Subject', icon: UserCog },
  { value: 'create_relationship', label: 'Create Relationship', icon: Link2 },
] as const

export type WorkflowActionTypeValue = (typeof WORKFLOW_ACTION_TYPES)[number]['value']

/** Options for combobox/select (value + label only). */
export const WORKFLOW_ACTION_TYPE_OPTIONS: { value: string; label: string }[] =
  WORKFLOW_ACTION_TYPES.map(({ value, label }) => ({ value, label }))

export function getActionTypeInfo(type: string): { label: string; icon: LucideIcon } {
  const found = WORKFLOW_ACTION_TYPES.find((o) => o.value === type)
  return found ? { label: found.label, icon: found.icon } : { label: type, icon: Zap }
}

/** Label by value (for simple lookups, e.g. ActionNode). */
export function getActionTypeLabel(type: string): string {
  return getActionTypeInfo(type).label
}
