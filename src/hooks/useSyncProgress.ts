import { useCallback, useEffect, useRef, useState } from 'react'
import { getAuthToken } from '@/lib/api-client'

export type SyncStage =
  | 'started'
  | 'fetching_messages'
  | 'processing_messages'
  | 'saving_events'
  | 'completed'
  | 'failed'

export interface SyncProgressEvent {
  type: 'sync_progress'
  account_id: string
  email_address: string
  stage: SyncStage
  message: string
  timestamp: string
  messages_fetched: number
  events_created: number
  error: string | null
}

interface WebSocketMessage {
  type: string
  [key: string]: unknown
}

interface UseSyncProgressOptions {
  enabled?: boolean
  onProgress?: (event: SyncProgressEvent) => void
  onError?: (error: Error) => void
}

interface SyncProgressState {
  [accountId: string]: SyncProgressEvent
}

/**
 * WebSocket hook for real-time email sync progress updates
 *
 * Connects to the backend WebSocket endpoint and receives
 * progress updates during email sync operations.
 */
export function useSyncProgress({
  enabled = true,
  onProgress,
  onError,
}: UseSyncProgressOptions = {}) {
  const wsRef = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isReconnecting, setIsReconnecting] = useState(false)
  const [syncProgress, setSyncProgress] = useState<SyncProgressState>({})
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
        const message: WebSocketMessage = JSON.parse(event.data)

        if (message.type === 'sync_progress') {
          const progressEvent = message as unknown as SyncProgressEvent

          // Update state for this account
          setSyncProgress((prev) => ({
            ...prev,
            [progressEvent.account_id]: progressEvent,
          }))

          // Call progress callback
          onProgress?.(progressEvent)

          // Clear completed/failed syncs after a delay
          if (progressEvent.stage === 'completed' || progressEvent.stage === 'failed') {
            setTimeout(() => {
              setSyncProgress((prev) => {
                const next = { ...prev }
                delete next[progressEvent.account_id]
                return next
              })
            }, 5000)
          }
        } else if (message.type === 'connected') {
          console.log('Sync progress WebSocket connected:', message.message)
        } else if (message.type === 'warning') {
          console.warn('Sync progress WebSocket warning:', message.message)
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err)
        onError?.(err instanceof Error ? err : new Error('Unknown error'))
      }
    },
    [onProgress, onError]
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
      // Get WebSocket URL from environment or construct from API URL
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const wsProtocol = apiUrl.startsWith('https') ? 'wss:' : 'ws:'
      const apiHost = new URL(apiUrl).host
      const wsUrl = `${wsProtocol}//${apiHost}/ws/sync-progress?token=${encodeURIComponent(token)}`

      wsRef.current = new WebSocket(wsUrl)

      wsRef.current.onopen = () => {
        console.log('Sync progress WebSocket connected')
        setIsConnected(true)
        setIsReconnecting(false)
        reconnectAttemptsRef.current = 0
      }

      wsRef.current.onmessage = handleMessage

      wsRef.current.onerror = (event) => {
        console.error('Sync progress WebSocket error:', event)
        onError?.(new Error('WebSocket error occurred'))
      }

      wsRef.current.onclose = (event) => {
        console.log('Sync progress WebSocket closed:', event.code, event.reason)
        setIsConnected(false)

        // Don't reconnect if closed due to auth failure
        if (event.code === 4001 || event.code === 4002) {
          console.warn('WebSocket auth failed, not reconnecting')
          return
        }

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
      setIsReconnecting(false)
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

  /**
   * Send ping to keep connection alive
   */
  const ping = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send('ping')
    }
  }, [])

  // Connect on mount when enabled, disconnect on unmount
  useEffect(() => {
    if (enabled) {
      connect()

      // Send ping every 30 seconds to keep connection alive
      const pingInterval = setInterval(ping, 30000)

      return () => {
        clearInterval(pingInterval)
        disconnect()
      }
    }
  }, [enabled, connect, disconnect, ping])

  /**
   * Get progress for a specific account
   */
  const getAccountProgress = useCallback(
    (accountId: string): SyncProgressEvent | null => {
      return syncProgress[accountId] || null
    },
    [syncProgress]
  )

  /**
   * Check if any account is currently syncing
   */
  const isAnySyncing = Object.values(syncProgress).some(
    (p) => p.stage !== 'completed' && p.stage !== 'failed'
  )

  return {
    isConnected,
    isReconnecting,
    syncProgress,
    isAnySyncing,
    getAccountProgress,
    reconnect: connect,
    disconnect,
  }
}

/**
 * Get human-readable status text for a sync stage
 */
export function getSyncStageText(stage: SyncStage): string {
  switch (stage) {
    case 'started':
      return 'Starting sync...'
    case 'fetching_messages':
      return 'Fetching messages...'
    case 'processing_messages':
      return 'Processing messages...'
    case 'saving_events':
      return 'Saving events...'
    case 'completed':
      return 'Sync completed'
    case 'failed':
      return 'Sync failed'
    default:
      return 'Unknown status'
  }
}

/**
 * Get progress percentage for a sync stage (approximate)
 */
export function getSyncStageProgress(stage: SyncStage): number {
  switch (stage) {
    case 'started':
      return 10
    case 'fetching_messages':
      return 30
    case 'processing_messages':
      return 60
    case 'saving_events':
      return 85
    case 'completed':
      return 100
    case 'failed':
      return 0
    default:
      return 0
  }
}
