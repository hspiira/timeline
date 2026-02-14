import { useCallback, useEffect, useRef, useState } from 'react'
import { getAuthToken } from '@/lib/api-client'
import type { Activity } from '@/lib/types/activity'

interface UseActivitySubscriptionOptions {
  enabled?: boolean
  onNewActivity?: (activity: Activity) => void
  onActivityUpdated?: (activity: Activity) => void
  onActivityRemoved?: (activityId: string) => void
  onError?: (error: Error) => void
}

type SubscriptionEvent =
  | { type: 'activity_created'; data: Activity }
  | { type: 'activity_updated'; data: Activity }
  | { type: 'activity_removed'; data: { id: string } }
  | { type: 'error'; data: { message: string } }

/**
 * WebSocket subscription hook for real-time activity updates
 *
 * In a production environment, this would connect to a WebSocket server
 * that broadcasts activity events in real-time.
 *
 * For now, it simulates real-time updates with polling as fallback.
 */
export function useActivitySubscription({
  enabled = true,
  onNewActivity,
  onActivityUpdated,
  onActivityRemoved,
  onError,
}: UseActivitySubscriptionOptions = {}) {
  const wsRef = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isReconnecting, setIsReconnecting] = useState(false)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const MAX_RECONNECT_ATTEMPTS = 5
  const RECONNECT_INTERVAL = 3000

  /**
   * Handle incoming WebSocket messages
   */
  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const message: SubscriptionEvent = JSON.parse(event.data)

        switch (message.type) {
          case 'activity_created':
            onNewActivity?.(message.data)
            break
          case 'activity_updated':
            onActivityUpdated?.(message.data)
            break
          case 'activity_removed':
            onActivityRemoved?.(message.data.id)
            break
          case 'error':
            onError?.(new Error(message.data.message))
            break
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err)
        onError?.(err instanceof Error ? err : new Error('Unknown error'))
      }
    },
    [onNewActivity, onActivityUpdated, onActivityRemoved, onError]
  )

  /**
   * Connect to WebSocket server
   */
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    const token = getAuthToken()
    if (!token) {
      console.warn('No auth token available for WebSocket connection')
      return
    }

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const wsProtocol = apiUrl.startsWith('https') ? 'wss:' : 'ws:'
      const apiHost = new URL(apiUrl).host
      const wsUrl = `${wsProtocol}//${apiHost}/api/v1/ws?token=${encodeURIComponent(token)}`

      wsRef.current = new WebSocket(wsUrl)

      wsRef.current.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        setIsReconnecting(false)
        reconnectAttemptsRef.current = 0
      }

      wsRef.current.onmessage = handleMessage

      wsRef.current.onerror = (event) => {
        console.error('WebSocket error:', event)
        onError?.(new Error('WebSocket error occurred'))
      }

      wsRef.current.onclose = () => {
        console.log('WebSocket closed')
        setIsConnected(false)
        attemptReconnect()
      }
    } catch (err) {
      console.error('Failed to create WebSocket:', err)
      onError?.(err instanceof Error ? err : new Error('Failed to create WebSocket'))
      attemptReconnect()
    }
  }, [handleMessage, onError])

  /**
   * Attempt to reconnect with exponential backoff
   */
  const attemptReconnect = useCallback(() => {
    if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
      console.warn(
        `Max reconnection attempts (${MAX_RECONNECT_ATTEMPTS}) reached. Giving up.`
      )
      return
    }

    setIsReconnecting(true)
    reconnectAttemptsRef.current += 1
    const delay = RECONNECT_INTERVAL * Math.pow(2, reconnectAttemptsRef.current - 1)

    reconnectTimeoutRef.current = setTimeout(() => {
      console.log(`Attempting to reconnect (attempt ${reconnectAttemptsRef.current})...`)
      connect()
    }, delay)
  }, [connect])

  /**
   * Subscribe to specific activity types
   */
  const subscribe = useCallback(
    (filters?: {
      actions?: string[]
      resourceTypes?: string[]
      userId?: string
    }) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            type: 'subscribe',
            filters,
          })
        )
      }
    },
    []
  )

  /**
   * Unsubscribe from activity updates
   */
  const unsubscribe = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'unsubscribe',
        })
      )
    }
  }, [])

  /**
   * Disconnect from WebSocket
   */
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
    setIsReconnecting(false)
    reconnectAttemptsRef.current = 0
  }, [])

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    if (enabled) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [enabled, connect, disconnect])

  return {
    isConnected,
    isReconnecting,
    reconnectAttempts: reconnectAttemptsRef.current,
    subscribe,
    unsubscribe,
    disconnect,
    reconnect: connect,
  }
}

/**
 * Simulated real-time activity generator for development/testing
 *
 * This generates mock activities at random intervals to simulate
 * a live activity feed. Remove in production.
 */
export function useSimulatedActivityStream(
  onNewActivity: (activity: Activity) => void,
  enabled = true
) {
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (!enabled) return

    const generateMockActivity = () => {
      const actions = ['created', 'updated', 'deleted', 'viewed', 'documented'] as const
      const resourceTypes = ['event', 'subject', 'document', 'workflow'] as const

      const mockActivity: Activity = {
        id: `activity_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        userId: `user_${Math.floor(Math.random() * 1000)}`,
        action: actions[Math.floor(Math.random() * actions.length)],
        resourceType: resourceTypes[Math.floor(Math.random() * resourceTypes.length)],
        resourceId: `resource_${Math.random().toString(36).substr(2, 9)}`,
        resourceName: `Resource ${Math.floor(Math.random() * 100)}`,
        timestamp: new Date(),
        priority: ['low', 'medium', 'high'][Math.floor(Math.random() * 3)] as any,
        description: 'Simulated activity for development',
      }

      onNewActivity(mockActivity)

      // Schedule next activity in 5-15 seconds
      const nextDelay = 5000 + Math.random() * 10000
      timeoutRef.current = setTimeout(generateMockActivity, nextDelay)
    }

    // Start generating activities
    timeoutRef.current = setTimeout(generateMockActivity, 3000)

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [enabled, onNewActivity])
}
