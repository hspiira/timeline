import { useState } from 'react'
import { Skeleton } from '@/components/ui/Skeleton'
import { DashboardCard } from './DashboardCard'

const TABS = ['New', 'Removed'] as const
const SKELETON_ROWS = 4

export function LatestTurnoverCard() {
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]>('New')

  return (
    <DashboardCard
      title="Latest changes"
      action={
        <a href="#" className="text-xs text-muted-foreground hover:text-[var(--dashboard-accent)]">
          View all &gt;
        </a>
      }
    >
      <div className="space-y-4">
        <div className="flex gap-1 border-b border-border/40 -mb-2">
          {TABS.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-[var(--dashboard-accent)] text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
        <ul className="space-y-3">
          {Array.from({ length: SKELETON_ROWS }).map((_, i) => (
            // biome-ignore lint/suspicious/noArrayIndexKey: fixed-length loading placeholder; the list never reorders.
            <li key={i} className="flex items-center gap-3">
              <Skeleton className="w-9 h-9 rounded-full shrink-0" />
              <div className="flex-1 min-w-0">
                <Skeleton className="h-4 w-24 mb-1" />
                <Skeleton className="h-3 w-16" />
              </div>
              <Skeleton className="h-3 w-14 shrink-0" />
            </li>
          ))}
        </ul>
      </div>
    </DashboardCard>
  )
}
