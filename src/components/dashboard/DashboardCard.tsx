import type { ReactNode } from 'react'

interface DashboardCardProps {
  title: string
  action?: ReactNode
  children: ReactNode
  className?: string
}

export function DashboardCard({ title, action, children, className = '' }: DashboardCardProps) {
  return (
    <div className={`rounded-none border border-border/60 bg-card/80 overflow-hidden ${className}`}>
      <div className="flex items-center justify-between gap-2 px-4 py-3 border-b border-border/40">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </div>
  )
}
