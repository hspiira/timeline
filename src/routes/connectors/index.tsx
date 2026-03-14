import { createFileRoute, redirect } from '@tanstack/react-router'
import { requireAuthBeforeLoad } from '@/lib/route-auth'

export const Route = createFileRoute('/connectors/')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
    throw redirect({ to: '/settings/connectors', replace: true })
  },
  component: ConnectorsRedirect,
})

function ConnectorsRedirect() {
  return null
}
