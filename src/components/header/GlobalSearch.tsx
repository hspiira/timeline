import { useNavigate } from '@tanstack/react-router'
import { Search } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

export function GlobalSearch() {
  const [q, setQ] = useState('')
  const navigate = useNavigate()

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = q.trim()
    if (trimmed) {
      navigate({ to: '/search', search: { q: trimmed, scope: 'all' } })
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-1 max-w-[220px]">
      <div className="relative flex-1 min-w-0">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
        <Input
          type="search"
          placeholder="Search…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="h-9 pl-8 py-1 text-sm bg-muted/50 border-border"
          aria-label="Global search"
        />
      </div>
      <Button
        type="submit"
        size="sm"
        variant="ghost"
        className="shrink-0 h-9 px-2"
        aria-label="Go to search"
      >
        <Search className="w-4 h-4" />
      </Button>
    </form>
  )
}
