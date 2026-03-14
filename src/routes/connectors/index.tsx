import { createFileRoute } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import { ConnectorsHealthPage } from '@/components/connectors/ConnectorsHealthPage'

export const Route = createFileRoute('/connectors/')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  component: ConnectorsHealthPage,
})
