import { useMemo } from 'react'

interface UseVirtualScrollOptions {
  itemCount: number
  enableThreshold?: number // Enable virtual scrolling when item count exceeds this
  manualEnable?: boolean
}

/**
 * Hook to determine if virtual scrolling should be enabled
 *
 * Virtual scrolling improves performance for large lists (1000+ items)
 * by only rendering visible items in the viewport.
 *
 * Usage:
 * ```tsx
 * const { shouldVirtualize, itemHeight } = useVirtualScroll({
 *   itemCount: feed.items.length,
 *   enableThreshold: 100, // Enable when > 100 items
 * })
 *
 * <ActivityFeed useVirtualScrolling={shouldVirtualize} />
 * ```
 */
export function useVirtualScroll({
  itemCount,
  enableThreshold = 100,
  manualEnable = false,
}: UseVirtualScrollOptions) {
  const shouldVirtualize = useMemo(() => {
    if (manualEnable) return true
    return itemCount > enableThreshold
  }, [itemCount, enableThreshold, manualEnable])

  return {
    shouldVirtualize,
    itemHeight: 100, // Standard activity renderer height
    listHeight: 600, // Default viewport height
    estimatedSize: itemCount, // For scroll position calculations
  }
}

export default useVirtualScroll
