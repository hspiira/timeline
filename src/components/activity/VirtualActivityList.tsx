import { useVirtualizer } from '@tanstack/react-virtual'
import { useRef } from 'react'
import type { Activity } from '@/lib/types/activity'
import { ActivityRenderer } from './ActivityRenderers'

interface VirtualActivityListProps {
  activities: Activity[]
  selectedId?: string | null
  expandedIds?: Set<string>
  onSelect?: (id: string) => void
  onExpand?: (id: string) => void
  height?: number
  itemHeight?: number
}

/**
 * Virtual scrolling component for large activity lists
 * Only renders visible items to improve performance
 *
 * Uses @tanstack/react-virtual for efficient rendering of 1000+ activities
 * with minimal memory footprint and smooth scrolling performance
 */
export function VirtualActivityList({
  activities,
  selectedId,
  onSelect,
  onExpand,
  height = 600,
  itemHeight = 100,
}: VirtualActivityListProps) {
  const parentRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: activities.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => itemHeight,
    // Overscan to smooth scrolling and prevent blank areas
    overscan: 10,
  })

  const items = virtualizer.getVirtualItems()
  const totalSize = virtualizer.getTotalSize()

  if (activities.length === 0) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        <span className="text-sm">No activities to display</span>
      </div>
    )
  }

  return (
    <div
      ref={parentRef}
      className="overflow-y-auto rounded-none border border-border/50 bg-card/50"
      style={{
        height,
      }}
    >
      <div
        style={{
          height: totalSize,
        }}
      >
        {items.map(virtualItem => {
          const activity = activities[virtualItem.index]
          if (!activity) return null

          return (
            <div
              key={virtualItem.key}
              style={{  
                position: 'absolute',  
                top: 0,  
                left: 0,  
                width: '100%',  
                transform: `translateY(${virtualItem.start}px)`,  
              }}
              className="px-3 py-2"
            >
              <ActivityRenderer
                activity={activity}
                isSelected={selectedId === activity.id}
                onSelect={onSelect}
                onExpand={onExpand}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default VirtualActivityList
