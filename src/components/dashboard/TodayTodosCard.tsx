import { Link } from '@tanstack/react-router'
import { addDays, format, isSameMonth, isToday, startOfWeek } from 'date-fns'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Skeleton } from '@/components/ui/Skeleton'
import { DashboardCard } from './DashboardCard'

/** Minimal event for today list */
interface TodayEvent {
  id: string
  event_time: string
  event_type: string
  subject_id?: string
}

interface TodayTodosCardProps {
  todayEvents?: TodayEvent[] | null
  loading?: boolean
}

export function TodayTodosCard({ todayEvents = [], loading = false }: TodayTodosCardProps) {
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date(), { weekStartsOn: 1 }))
  const weekDays = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)),
    [weekStart],
  )
  const today = new Date()

  const items = useMemo(() => {
    if (!todayEvents?.length) return []
    return todayEvents
      .map((e) => ({ ...e, date: new Date(e.event_time) }))
      .sort((a, b) => a.date.getTime() - b.date.getTime())
      .slice(0, 5)
  }, [todayEvents])

  return (
    <DashboardCard
      title="Today's to-dos"
      action={
        <Link
          to="/events"
          className="text-xs text-muted-foreground hover:text-[var(--dashboard-accent)]"
        >
          View all &gt;
        </Link>
      }
    >
      <div className="space-y-4">
        <p className="text-sm font-medium text-foreground tabular-nums">
          {format(today, 'yyyy/MM/dd')}
        </p>

        {/* Mini week calendar */}
        <div className="flex items-center justify-between gap-1">
          <button
            type="button"
            onClick={() => setWeekStart((d) => addDays(d, -7))}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded-none"
            aria-label="Previous week"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <div className="flex gap-1 flex-1 justify-center">
            {weekDays.map((d) => (
              <button
                key={d.toISOString()}
                type="button"
                onClick={() => setWeekStart(startOfWeek(d, { weekStartsOn: 1 }))}
                className={`w-8 h-8 text-xs font-medium rounded-none flex items-center justify-center ${
                  isToday(d)
                    ? 'bg-[var(--dashboard-accent)] text-primary-foreground'
                    : isSameMonth(d, today)
                      ? 'text-foreground hover:bg-muted'
                      : 'text-muted-foreground hover:bg-muted'
                }`}
              >
                {format(d, 'd')}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={() => setWeekStart((d) => addDays(d, 7))}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded-none"
            aria-label="Next week"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
        <button
          type="button"
          className="w-full text-xs text-muted-foreground hover:text-foreground py-1"
          onClick={() => setWeekStart(startOfWeek(new Date(), { weekStartsOn: 1 }))}
        >
          Back to today
        </button>

        {/* Today's list */}
        <ul className="space-y-2 border-t border-border/40 pt-3">
          {loading
            ? Array.from({ length: 3 }).map((_, i) => (
                <li key={i} className="flex gap-2">
                  <Skeleton className="h-4 w-10 shrink-0" />
                  <div className="flex-1">
                    <Skeleton className="h-4 w-full mb-1" />
                    <Skeleton className="h-3 w-2/3" />
                  </div>
                </li>
              ))
            : items.length > 0
              ? items.map((e) => (
                  <li key={e.id} className="flex gap-2 text-sm">
                    <span className="text-muted-foreground tabular-nums shrink-0">
                      {format(new Date(e.event_time), 'HH:mm')}
                    </span>
                    <div className="min-w-0">
                      <p className="font-medium text-foreground truncate">{e.event_type}</p>
                      <p className="text-xs text-muted-foreground truncate">Event</p>
                    </div>
                  </li>
                ))
              : [
                  <li key="empty" className="text-sm text-muted-foreground py-2">
                    No events scheduled for today
                  </li>,
                ]}
        </ul>
      </div>
    </DashboardCard>
  )
}
