/**
 * Import a workflow from a requirements JSON file (e.g. workflow-new-client-rollout-v2.json)
 * and create it via the Timeline API.
 *
 * Usage:
 *   1. Start the backend server
 *   2. Log in to the UI and get your auth token (e.g. localStorage.getItem("auth_token"))
 *   3. Run: npx tsx scripts/import-workflow.ts <AUTH_TOKEN> [path-to.json]
 *
 * Default path: docs/workflow-new-client-rollout-v2.json
 *
 * Environment:
 *   API_URL - API base URL (default: http://localhost:8000)
 *   TENANT_ID - Optional X-Tenant-ID header if your backend requires it
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const API_URL = (process.env.API_URL || 'http://localhost:8000').replace(/\/$/, '')
const TENANT_ID = process.env.TENANT_ID

interface TaskInput {
  id?: string
  name: string
  description?: string
  documentIds?: string[]
  variables?: Record<string, unknown>
}

interface StepInput {
  id: string
  name: string
  description?: string
  condition?: string
  reject_to_step_id?: string
  tasks?: TaskInput[]
}

interface WorkflowInput {
  _version?: string
  _comment?: string
  name: string
  description?: string
  trigger_event_type?: string
  steps: StepInput[]
}

function buildCreatePayload(input: WorkflowInput) {
  const trigger = (input.trigger_event_type || '').trim() || 'client_instruction.received'
  const actions = input.steps.map((step) => ({
    type: 'create_event',
    params: {
      stepName: step.name,
      stepDescription: step.description,
      condition: step.condition,
      ...(step.reject_to_step_id != null && { reject_to_step_id: step.reject_to_step_id }),
      tasks: (step.tasks ?? []).map((t) => ({
        name: t.name,
        description: t.description,
        variables: t.variables,
        documentIds: t.documentIds,
      })),
    },
  }))

  return {
    name: input.name,
    description: input.description ?? null,
    trigger_event_type: trigger,
    actions,
    execution_order: 0,
    is_active: true,
  }
}

async function importWorkflow(token: string, jsonPath: string) {
  const absolutePath = resolve(process.cwd(), jsonPath)
  console.log(`📂 Reading ${absolutePath}`)
  const raw = readFileSync(absolutePath, 'utf-8')
  const parsed = JSON.parse(raw) as WorkflowInput

  if (!parsed.name || !Array.isArray(parsed.steps)) {
    throw new Error('Invalid workflow JSON: must have "name" and "steps" array')
  }

  const payload = buildCreatePayload(parsed)
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }
  if (TENANT_ID) headers['X-Tenant-ID'] = TENANT_ID

  const url = `${API_URL}/api/v1/workflows`
  console.log(`📡 POST ${url}`)
  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`API error ${response.status}: ${text}`)
  }

  const data = (await response.json()) as { id: string; name: string }
  console.log(`✅ Workflow created: ${data.name} (id: ${data.id})`)
  return data
}

const token = process.argv[2]
const jsonPath = process.argv[3] || 'docs/workflow-new-client-rollout-v2.json'

if (!token) {
  console.error('❌ Error: Auth token required')
  console.log('\nUsage:')
  console.log('  npx tsx scripts/import-workflow.ts <AUTH_TOKEN> [path-to.json]')
  console.log('\nDefault path: docs/workflow-new-client-rollout-v2.json')
  console.log('\nTo get your auth token:')
  console.log('  1. Log in to the UI')
  console.log('  2. Open browser console and run: localStorage.getItem("auth_token")')
  process.exit(1)
}

importWorkflow(token, jsonPath)
  .then(() => process.exit(0))
  .catch((err) => {
    console.error('❌', err.message)
    process.exit(1)
  })
