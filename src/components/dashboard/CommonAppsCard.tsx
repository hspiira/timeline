import { Link } from '@tanstack/react-router'
import { ClipboardList, FileText, GitBranch, Mail, TrendingUp, Users } from 'lucide-react'
import { DashboardCard } from './DashboardCard'

const APPS = [
  { to: '/email-accounts', icon: Mail, label: 'Email' },
  { to: '/events', icon: ClipboardList, label: 'Events' },
  { to: '/flows', icon: GitBranch, label: 'Flows' },
  { to: '/events', icon: TrendingUp, label: 'Analytics' },
  { to: '/subjects', icon: Users, label: 'Subjects' },
  { to: '/subjects', icon: FileText, label: 'Documents' },
] as const

export function CommonAppsCard() {
  return (
    <DashboardCard
      title="Common applications"
      action={
        <Link to="/" className="text-xs text-muted-foreground hover:text-[var(--dashboard-accent)]">
          All apps &gt;
        </Link>
      }
    >
      <div className="grid grid-cols-3 gap-3">
        {APPS.map(({ to, icon: Icon, label }) => (
          <Link
            key={label}
            to={to}
            className="flex flex-col items-center justify-center gap-2 p-3 rounded-none border border-border/40 bg-muted/20 hover:border-[var(--dashboard-accent)]/40 hover:bg-muted/40 transition-colors"
          >
            <div className="w-9 h-9 rounded-none flex items-center justify-center bg-[var(--dashboard-accent-muted)] text-[var(--dashboard-accent)]">
              <Icon className="w-4 h-4" strokeWidth={1.75} />
            </div>
            <span className="text-xs font-medium text-foreground">{label}</span>
          </Link>
        ))}
      </div>
    </DashboardCard>
  )
}
