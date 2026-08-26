import { useState } from 'react'
import { Skeleton } from '@/components/ui/Skeleton'
import { DashboardCard } from './DashboardCard'

const TABS = ['FAQ', 'Guides', 'Contracts'] as const
const SKELETON_LINKS = 5

export function HelpCenterCard() {
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]>('FAQ')

  return (
    <DashboardCard
      title="Help center"
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
        <ul className="space-y-2">
          {Array.from({ length: SKELETON_LINKS }).map((_, i) => (
            // biome-ignore lint/suspicious/noArrayIndexKey: fixed-length loading placeholder; the list never reorders.
            <li key={i}>
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-3 w-4/5 mt-1" />
            </li>
          ))}
        </ul>
      </div>
    </DashboardCard>
  )
}
