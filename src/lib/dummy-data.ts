import type { EventResponse } from './types'

export const dummyEvents: EventResponse[] = [
  {
    id: 'evt_001',
    subject_id: 'subj_user_12345',
    event_type: 'user.logged_in',
    schema_version: 1,
    event_time: '2024-12-18T14:30:00Z',
    payload: { ip_address: '192.168.1.100', device: 'desktop', browser: 'Chrome' },
    hash: 'abc123def456'
  },
  {
    id: 'evt_002',
    subject_id: 'subj_order_67890',
    event_type: 'order.shipped',
    schema_version: 1,
    event_time: '2024-12-18T13:15:00Z',
    payload: { carrier: 'FedEx', tracking_number: '1Z999AA10123456784', destination: 'New York' },
    hash: 'def456ghi789'
  },
  {
    id: 'evt_003',
    subject_id: 'subj_user_12345',
    event_type: 'user.profile_updated',
    schema_version: 1,
    event_time: '2024-12-18T11:45:00Z',
    payload: { field: 'bio', old_value: null, new_value: 'Software Developer at TechCorp' },
    hash: 'ghi789jkl012'
  },
  {
    id: 'evt_004',
    subject_id: 'subj_project_abc123',
    event_type: 'project.milestone_completed',
    schema_version: 1,
    event_time: '2024-12-18T10:20:00Z',
    payload: { milestone: 'Phase 1 - Authentication', completion_rate: '100%', team_size: 3 },
    hash: 'jkl012mno345'
  },
  {
    id: 'evt_005',
    subject_id: 'subj_order_67890',
    event_type: 'order.placed',
    schema_version: 1,
    event_time: '2024-12-17T16:00:00Z',
    payload: { total_amount: 299.99, items_count: 3, payment_method: 'credit_card' },
    hash: 'mno345pqr678'
  }
]

export const dummyStats = {
  totalSubjects: 3,
  subjectsThisWeek: 2,
  totalEvents: 5,
  activeWorkflows: 0
}
