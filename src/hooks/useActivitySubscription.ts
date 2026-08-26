import { useCallback, useEffect, useRef, useState } from 'react'
import { getApiBaseUrl, getAuthToken } from '@/lib/api-client'
import type { Activity } from '@/lib/types/activity'

interface UseActivitySubscriptionOptions {
  enabled?: boolean
  /** Filter stream to this subject (backend query param). */
  subjectId?: string | null
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
 * Build SSE stream URL for the events stream (roadmap: /api/v1/events/stream).
 * EventSource does not support custom headers in the browser, so auth is passed as query param.
 * Optional subject_id filters server-side to that subject.
 */
export function getEventsStreamUrl(subjectId?: string | null): string | null {
  const token = getAuthToken()
  if (!token) return null
  const base = getApiBaseUrl().replace(/\/$/, '')
  const params = new URLSearchParams({ token })
  if (subjectId) params.set('subject_id', subjectId)
  return `${base}/api/v1/events/stream?${params.toString()}`
}

/**
 * SSE subscription hook for real-time activity updates.
 * Connects to GET /api/v1/events/stream (roadmap: EventSource for SSE).
 * Preserves reconnection with exponential backoff and the same callback API as before.
 */
export function useActivitySubscription({
  enabled = true,
  subjectId = null,
  onNewActivity,
  onActivityUpdated,
  onActivityRemoved,
  onError,
}: UseActivitySubscriptionOptions = {}) {
  const eventSourceRef = useRef<EventSource | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isReconnecting, setIsReconnecting] = useState(false)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const MAX_RECONNECT_ATTEMPTS = 5
  const RECONNECT_INTERVAL = 3000
  const subjectIdRef = useRef(subjectId)
  subjectIdRef.current = subjectId

  const dispatchEvent = useCallback(
    (message: SubscriptionEvent) => {
      try {
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
        onError?.(err instanceof Error ? err : new Error('Unknown error'))
      }
    },
    [onNewActivity, onActivityUpdated, onActivityRemoved, onError],
  )

  /**
   * Handle SSE message: support both named events (event: activity_created + data: {...}) and
   * generic message with data: { type, data }.
   */
  const handleSSEMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const raw = event.data
        if (typeof raw !== 'string') return
        const parsed = JSON.parse(raw) as Record<string, unknown>
        const eventType = event.type as string
        if (eventType !== 'message') {
          if (eventType === 'activity_created')
            dispatchEvent({ type: 'activity_created', data: parsed as unknown as Activity })
          else if (eventType === 'activity_updated')
            dispatchEvent({ type: 'activity_updated', data: parsed as unknown as Activity })
          else if (eventType === 'activity_removed')
            dispatchEvent({ type: 'activity_removed', data: { id: (parsed?.id as string) ?? '' } })
          else if (eventType === 'error')
            dispatchEvent({
              type: 'error',
              data: { message: (parsed?.message as string) ?? 'Unknown error' },
            })
          return
        }
        const msg = parsed as SubscriptionEvent
        if (msg.type) dispatchEvent(msg)
      } catch (err) {
        console.error('Failed to parse SSE message:', err)
        onError?.(err instanceof Error ? err : new Error('Unknown error'))
      }
    },
    [dispatchEvent, onError],
  )

  const attemptReconnectRef = useRef<() => void>(() => {})

  const connect = useCallback(() => {
    if (eventSourceRef.current?.readyState === EventSource.OPEN) return

    const url = getEventsStreamUrl(subjectIdRef.current)
    if (!url) {
      console.warn('No auth token available for SSE connection')
      return
    }

    try {
      const es = new EventSource(url)
      eventSourceRef.current = es

      es.onopen = () => {
        console.log('SSE connected')
        setIsConnected(true)
        setIsReconnecting(false)
        reconnectAttemptsRef.current = 0
      }

      es.onmessage = handleSSEMessage
      es.addEventListener('activity_created', handleSSEMessage)
      es.addEventListener('activity_updated', handleSSEMessage)
      es.addEventListener('activity_removed', handleSSEMessage)

      es.onerror = () => {
        setIsConnected(false)
        es.close()
        eventSourceRef.current = null
        attemptReconnectRef.current()
      }
    } catch (err) {
      console.error('Failed to create EventSource:', err)
      onError?.(err instanceof Error ? err : new Error('Failed to create EventSource'))
      attemptReconnectRef.current()
    }
  }, [handleSSEMessage, onError])

  const attemptReconnect = useCallback(() => {
    if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
      console.warn(`Max reconnection attempts (${MAX_RECONNECT_ATTEMPTS}) reached. Giving up.`)
      return
    }
    setIsReconnecting(true)
    reconnectAttemptsRef.current += 1
    const delay = RECONNECT_INTERVAL * 2 ** (reconnectAttemptsRef.current - 1)
    reconnectTimeoutRef.current = setTimeout(() => {
      console.log(`Attempting to reconnect (attempt ${reconnectAttemptsRef.current})...`)
      connect()
    }, delay)
  }, [connect])

  useEffect(() => {
    attemptReconnectRef.current = attemptReconnect
  }, [attemptReconnect])

  const subscribe = useCallback(
    (_filters?: { actions?: string[]; resourceTypes?: string[]; userId?: string }) => {
      // SSE does not support client-side subscribe; server decides what to stream.
    },
    [],
  )

  const unsubscribe = useCallback(() => {
    // No-op for SSE; disconnect closes the stream.
  }, [])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setIsConnected(false)
    setIsReconnecting(false)
    reconnectAttemptsRef.current = 0
  }, [])

  useEffect(() => {
    if (enabled) connect()
    return () => disconnect()
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

/** Alias for useActivitySubscription; use for dashboard and subject timeline SSE. */
export const useEventStream = useActivitySubscription

/**
 * Simulated real-time activity generator for development/testing
 *
 * This generates mock activities at random intervals to simulate
 * a live activity feed. Remove in production.
 */
export function useSimulatedActivityStream(
  onNewActivity: (activity: Activity) => void,
  enabled = true,
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
        priority: (['low', 'medium', 'high'] as const)[Math.floor(Math.random() * 3)],
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
