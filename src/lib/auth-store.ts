import { Store } from '@tanstack/store'
import type { UserResponse } from '@/lib/types'
import {
  getAuthToken,
  refreshAccessToken,
  setAuthToken,
  setTenantId,
  timelineApi,
} from './api-client'
import { getApiErrorDisplay } from './api-utils'

interface AuthState {
  user: UserResponse | null
  token: string | null
  isLoading: boolean
  error: string | null
}

const initialState: AuthState = {
  user: null,
  token: null,
  isLoading: false,
  error: null,
}

export const authStore = new Store(initialState)

export const authActions = {
  /** Which organisations can this email sign in to? Empty means unknown email. */
  async organisationsForEmail(email: string) {
    const response = await timelineApi.auth.organisations(email.trim())
    if (response.error) return []
    return response.data?.organisations ?? []
  },

  /**
   * Sign in with email and password. Pass `tenant_id` only when the email belongs to
   * several organisations; for the common single-organisation case, omit it and the
   * user is never asked.
   */
  async login(email: string, password: string, tenant_id?: string) {
    authStore.setState((state) => ({ ...state, isLoading: true, error: null }))

    try {
      const response = await timelineApi.auth.login(email, password, tenant_id)

      if (response.error) {
        const display = getApiErrorDisplay(
          { error: response.error, status: response.response?.status },
          'Invalid credentials',
        )
        throw new Error(display.message)
      }

      const data = response.data
      if (!data) throw new Error('Invalid credentials')
      const { access_token } = data
      setAuthToken(access_token)

      const userResponse = (await timelineApi.users.me()) as {
        data?: UserResponse
        error?: unknown
        response?: { status?: number }
      }

      if (userResponse.error) {
        setAuthToken(null)
        setTenantId(null)
        const display = getApiErrorDisplay(
          { error: userResponse.error, status: userResponse.response?.status },
          'Failed to fetch user info',
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
      const errorMessage = error instanceof Error ? error.message : 'Login failed'
      authStore.setState({
        user: null,
        token: null,
        isLoading: false,
        error: errorMessage,
      })
      throw error
    }
  },

  /** C2 only: no admin_initial_password. Backend returns set_password_url for admin to set password. */
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
      const errorMessage = error instanceof Error ? error.message : 'Tenant creation failed'
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

  /**
   * Restore session on app load (e.g. after page reload).
   * If there is no in-memory token, calls POST /api/v1/auth/refresh with credentials: 'include'
   * (httpOnly cookie) to get a new access token. Then fetches user via me().
   * Backend must set refresh token cookie on login for this to work.
   */
  async initAuth() {
    let token = getAuthToken()
    if (!token && typeof window !== 'undefined') {
      token = await refreshAccessToken()
      if (token) setAuthToken(token)
    }
    if (!token) {
      return
    }

    if (typeof window !== 'undefined') {
      const stored = window.localStorage.getItem('tenant_id')
      if (stored) setTenantId(stored)
    }

    const state = authStore.state
    if (state.user && state.token === token) {
      return
    }

    authStore.setState((s) => ({ ...s, isLoading: true }))

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

      const userData = response.data
      if (userData) setTenantId(userData.tenant_id)

      authStore.setState((prev) => ({
        ...prev,
        user: userData ?? null,
        token,
        isLoading: false,
        error: null,
      }))
    } catch {
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
