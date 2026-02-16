import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect } from 'react'

export const Route = createFileRoute('/settings/workflows/create')({
  component: CreateWorkflowRedirect,
})

function CreateWorkflowRedirect() {
  const navigate = useNavigate()
  useEffect(() => {
    navigate({ to: '/settings/workflows' })
  }, [navigate])
  return null
}
