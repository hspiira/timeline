import { Link } from '@tanstack/react-router'
import type { ColumnDef } from '@tanstack/react-table'
import { DataTable } from '@/components/ui/DataTable'
import type { components } from '@/lib/timeline-api'
import type { FlowResponse } from '@/lib/types'

type Workflow = components['schemas']['WorkflowResponse']

export function FlowsTable({ flows, workflows }: { flows: FlowResponse[]; workflows: Workflow[] }) {
  const columns: Array<ColumnDef<FlowResponse>> = [
    {
      accessorKey: 'name',
      header: 'Name',
      cell: ({ row }) => {
        const flow = row.original
        return (
          <Link
            to="/flows/$flowId"
            params={{ flowId: flow.id }}
            className="font-medium text-primary hover:underline"
          >
            {flow.name}
          </Link>
        )
      },
    },
    {
      id: 'workflow',
      header: 'Workflow',
      cell: ({ row }) => {
        const flow = row.original
        if (!flow.workflow_id) return '\u2014'
        const w = workflows.find((x) => x.id === flow.workflow_id)
        if (!w) return flow.workflow_id
        return (
          <Link to="/settings/workflows" className="text-muted-foreground hover:text-foreground">
            {w.name}
          </Link>
        )
      },
    },
    {
      id: 'hierarchy',
      header: 'Hierarchy',
      cell: ({ row }) => {
        const hv = row.original.hierarchy_values
        if (!hv || Object.keys(hv).length === 0) return '\u2014'
        return (
          <span className="text-muted-foreground text-sm">
            {Object.entries(hv)
              .map(([k, v]) => `${k}: ${v}`)
              .join(', ')}
          </span>
        )
      },
    },
  ]

  return (
    <DataTable data={flows} columns={columns} isLoading={false} isEmpty={false} variant="default" />
  )
}
