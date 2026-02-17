import { useEffect } from "react"
import { authStore } from "@/lib/auth-store"
import { useNavigate } from "@tanstack/react-router"
import { useStore } from "@tanstack/react-store"

export function useRequireAuth() {
  const authState = useStore(authStore)
  const navigate = useNavigate()

useEffect(() => {
    if (!authState.isLoading && !authState.user) {
        navigate({ to: '/login', search: { tenant: '', redirect: undefined } })
    }
    }, [authState.isLoading, authState.user, navigate])

  return authState
}