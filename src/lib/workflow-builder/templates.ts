/**
 * Workflow templates – pre-built workflows for common patterns (Attio-style).
 * See: https://attio.com/help/reference/attio-101/introduction-to-workflows
 */

import type { Workflow } from './types'
import { createNode, createEdge, DEFAULT_TRIGGER_NODE_ID } from './types'
import { generateEdgeId } from './edge-manager'

export interface WorkflowTemplate {
  id: string
  name: string
  category: string
  description: string
  /** Optional tips keyed by node id, shown in the config panel when that node is selected. */
  stepTips?: Record<string, string>
  /** Build the initial workflow. workflowId and name are passed so the workflow can be used in the canvas. */
  buildWorkflow: (workflowId: string, workflowName: string) => Workflow
}

/** Churn monitor – trigger on an event, filter by condition, then run an action (e.g. create event / task). */
const churnMonitorTemplate: WorkflowTemplate = {
  id: 'churn-monitor',
  name: 'Churn monitor',
  category: 'Product-led Growth',
  description:
    'Automatically run a follow-up when a subscription or status changes (e.g. cancelled). Configure the trigger event, add a condition to filter, then an action such as creating an event or updating a record.',
  stepTips: {
    [DEFAULT_TRIGGER_NODE_ID]:
      'Set up this workflow to run when an event is created (e.g. subscription status change or record update). Pick the event type that indicates the change you want to react to.',
    'condition-1':
      'Check that the condition is met (e.g. status equals "Cancelled" or a specific attribute value). Only when this is true will the workflow continue to the next step.',
    'action-1':
      'Add the action to run when the condition passes – for example create an event, send an email, or update a subject. You can add more steps below by connecting from here.',
  },
  buildWorkflow(workflowId: string, workflowName: string): Workflow {
    const triggerId = DEFAULT_TRIGGER_NODE_ID
    const conditionId = 'condition-1'
    const actionId = 'action-1'
    const terminalId = 'terminal-false'
    const nodes = [
      createNode(triggerId, 'trigger', { x: 0, y: 0 }, {
        eventType: '',
        description: 'No description',
      }),
      createNode(conditionId, 'condition', { x: 0, y: 160 }, {
        expression: '',
        description: 'Did status change to cancelled?',
      }),
      createNode(actionId, 'action', { x: 0, y: 320 }, {
        actionType: 'create_event',
        params: {},
        description: 'Create follow-up event or task',
      }),
      createNode(terminalId, 'terminal', { x: 200, y: 260 }, {}),
    ]
    const edges = [
      createEdge(generateEdgeId(), triggerId, conditionId),
      createEdge(generateEdgeId(), conditionId, actionId, 'true'),
      createEdge(generateEdgeId(), conditionId, terminalId, 'false'),
    ]
    return { id: workflowId, name: workflowName, nodes, edges }
  },
}

export const WORKFLOW_TEMPLATES: WorkflowTemplate[] = [churnMonitorTemplate]

export function getWorkflowTemplate(id: string): WorkflowTemplate | undefined {
  return WORKFLOW_TEMPLATES.find((t) => t.id === id)
}
