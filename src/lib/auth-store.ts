import { Store } from '@tanstack/store'
import { timelineApi, setAuthToken, getAuthToken, setTenantId } from './api-client'
import { getApiErrorDisplay } from './api-utils'
import type { UserResponse } from '@/lib/types'

interface AuthState {
  user: UserResponse | null
  token: string | null
  isLoading: boolean
  error: string | null
}

const initialState: AuthState = {
  user: null,
  token: getAuthToken(),
  isLoading: false,
  error: null,
}

export const authStore = new Store(initialState)

export const authActions = {
  async login(username: string, password: string, tenant_code: string) {
    authStore.setState((state) => ({ ...state, isLoading: true, error: null }))

    try {
      const response = await timelineApi.auth.login(username, password, tenant_code)

      if (response.error) {
        const display = getApiErrorDisplay(
          { error: response.error, status: response.response?.status },
          'Invalid credentials'
        )
        throw new Error(display.message)
      }

      const { access_token } = response.data
      setAuthToken(access_token)

      const userResponse = await timelineApi.users.me() as {
        data?: UserResponse
        error?: unknown
        response?: { status?: number }
      }

      if (userResponse.error) {
        setAuthToken(null)
        setTenantId(null)
        const display = getApiErrorDisplay(
          { error: userResponse.error, status: userResponse.response?.status },
          'Failed to fetch user info'
        )
        throw new Error(display.message)
      }

      const user = userResponse.data
      if (!user) {
        setAuthToken(null)
        setTenantId(null)
        throw new Error('Failed to fetch user info')
      }

      setTenantId(user.tenant_id)

      authStore.setState({
        user,
        token: access_token,
        isLoading: false,
        error: null,
      })

      return user
    } catch (error) {
      setAuthToken(null)
      setTenantId(null)
      const errorMessage =
        error instanceof Error ? error.message : 'Login failed'
      authStore.setState({
        user: null,
        token: null,
        isLoading: false,
        error: errorMessage,
      })
      throw error
    }
  },

  async registerTenant(data: { code: string; name: string }) {
    authStore.setState((state) => ({ ...state, isLoading: true, error: null }))

    try {
      const response = await timelineApi.tenants.create(data)

      if (response.error) {
        const errorDetail =
          (response.error as { detail?: string })?.detail || 'Tenant creation failed'
        throw new Error(errorDetail)
      }

      authStore.setState((state) => ({ ...state, isLoading: false }))
      return response.data
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Tenant creation failed'
      authStore.setState((state) => ({
        ...state,
        isLoading: false,
        error: errorMessage,
      }))
      throw error
    }
  },

  logout() {
    setAuthToken(null)
    setTenantId(null)
    authStore.setState({
      user: null,
      token: null,
      isLoading: false,
      error: null,
    })
  },

  async initAuth() {
    const token = getAuthToken()

    if (!token) {
      return
    }

    if (typeof window !== 'undefined') {
      const stored = window.localStorage.getItem('tenant_id')
      if (stored) setTenantId(stored)
    }

    authStore.setState((state) => ({ ...state, isLoading: true }))

    try {
      const response = await timelineApi.users.me()

      if (response.error) {
        setAuthToken(null)
        setTenantId(null)
        authStore.setState({
          user: null,
          token: null,
          isLoading: false,
          error: null,
        })
        return
      }

      setTenantId(response.data.tenant_id)

      authStore.setState({
        user: response.data,
        token,
        isLoading: false,
        error: null,
      })
    } catch (error) {
      setAuthToken(null)
      setTenantId(null)
      authStore.setState({
        user: null,
        token: null,
        isLoading: false,
        error: null,
      })
    }
  },

  clearError() {
    authStore.setState((state) => ({ ...state, error: null }))
  },
}
