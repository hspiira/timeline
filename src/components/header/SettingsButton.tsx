import { Link } from '@tanstack/react-router'
import { Settings } from 'lucide-react'

export function SettingsButton() {
  return (
    <Link
      to="/settings/roles"
      className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-foreground/70 hover:text-foreground hover:bg-accent rounded-none transition-all"
      title="Settings"
      aria-label="Settings"
    >
      <Settings className="w-4 h-4" />
    </Link>
  )
}
