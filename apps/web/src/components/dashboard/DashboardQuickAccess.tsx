import { Link } from '@tanstack/react-router'
import { Calendar, GitBranch, Mail, Settings, Users } from 'lucide-react'

const TILES = [
  { to: '/events', icon: Calendar, label: 'Events' },
  { to: '/subjects', icon: Users, label: 'Subjects' },
  { to: '/flows', icon: GitBranch, label: 'Flows' },
  { to: '/email-accounts', icon: Mail, label: 'Email' },
  { to: '/settings', icon: Settings, label: 'Settings' },
] as const

export function DashboardQuickAccess() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
      {TILES.map(({ to, icon: Icon, label }) => (
        <Link
          key={to}
          to={to}
          className="flex flex-col items-center justify-center gap-2 p-4 rounded-none border border-border/60 bg-card/80 backdrop-blur-sm transition-all duration-200 hover:border-[var(--dashboard-accent)]/50 hover:bg-card hover:shadow-sm"
        >
          <div className="w-10 h-10 rounded-none flex items-center justify-center bg-[var(--dashboard-accent-muted)] text-[var(--dashboard-accent)]">
            <Icon className="w-5 h-5" strokeWidth={1.75} />
          </div>
          <span className="text-xs font-medium text-foreground">{label}</span>
        </Link>
      ))}
    </div>
  )
}
