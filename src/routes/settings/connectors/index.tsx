import { createFileRoute } from '@tanstack/react-router'
import { ConnectorsHealthPage } from '@/components/connectors/ConnectorsHealthPage'
import { requireAuthBeforeLoad } from '@/lib/route-auth'

export const Route = createFileRoute('/settings/connectors/')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  component: ConnectorsHealthPage,
})
