import { Store } from '@tanstack/store'
import { timelineApi, setAuthToken, getAuthToken, setTenantId } from './api-client'
import type { UserResponse } from '@/lib/types'

// Auth state interface
interface AuthState {
  user: UserResponse | null
  token: string | null
  isLoading: boolean
  error: string | null
}

// Initial state
const initialState: AuthState = {
  user: null,
  token: getAuthToken(),
  isLoading: false,
  error: null,
}

// Create auth store
export const authStore = new Store(initialState)

// Auth actions
export const authActions = {
  async login(username: string, password: string, tenant_code: string) {
    authStore.setState((state) => ({ ...state, isLoading: true, error: null }))

    try {
      const response = await timelineApi.auth.login(username, password, tenant_code)

      if (response.error) {
        throw new Error('Invalid credentials')
      }

      const { access_token } = response.data
      // Temporarily set token for the user fetch request
      setAuthToken(access_token)

      // Fetch user info
      const userResponse = await timelineApi.users.me()

      if (userResponse.error) {
        // Clear token if user fetch fails to prevent inconsistent state
        setAuthToken(null)
        setTenantId(null)
        throw new Error('Failed to fetch user info')
      }

      // Set tenant ID for X-Tenant-ID header on subsequent requests
      setTenantId(userResponse.data.tenant_id)

      authStore.setState({
        user: userResponse.data,
        token: access_token,
        isLoading: false,
        error: null,
      })

      return userResponse.data
    } catch (error) {
      // Ensure token and tenant are cleared on any error
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

    authStore.setState((state) => ({ ...state, isLoading: true }))

    try {
      const response = await timelineApi.users.me()

      if (response.error) {
        // Token invalid, clear it
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

      // Restore tenant ID from user data
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
