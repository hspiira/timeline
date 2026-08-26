import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { Calendar, FileText, Loader2, Search as SearchIcon, Users } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { SingleSelectCombobox } from '@/components/ui/combobox'
import { Input } from '@/components/ui/input'
import { timelineApi } from '@/lib/api-client'
import { requireAuthBeforeLoad } from '@/lib/route-auth'
import type { components } from '@/lib/timeline-api'

export const Route = createFileRoute('/search/')({
  beforeLoad: () => {
    requireAuthBeforeLoad()
  },
  validateSearch: (search: Record<string, unknown>) => ({
    q: typeof search.q === 'string' ? search.q : '',
    scope:
      typeof search.scope === 'string' &&
      ['all', 'subjects', 'events', 'documents'].includes(search.scope)
        ? search.scope
        : 'all',
  }),
  component: SearchPage,
})

type SearchResultItem = components['schemas']['SearchResultItemResponse']

const SCOPE_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'subjects', label: 'Subjects' },
  { value: 'events', label: 'Events' },
  { value: 'documents', label: 'Documents' },
] as const

function ResultLink({ item }: { item: SearchResultItem }) {
  const type = item.resource_type
  if (type === 'subject') {
    return (
      <Link
        to="/subjects/$subjectId"
        params={{ subjectId: item.id }}
        search={{ tab: 'events', event_id: undefined }}
        className="text-primary hover:underline font-medium"
      >
        {item.display_title}
      </Link>
    )
  }
  if (type === 'event' && item.subject_id) {
    return (
      <Link
        to="/subjects/$subjectId/events/$eventId"
        params={{ subjectId: item.subject_id, eventId: item.id }}
        className="text-primary hover:underline font-medium"
      >
        {item.display_title}
      </Link>
    )
  }
  if (type === 'document' && item.subject_id) {
    return (
      <Link
        to="/subjects/$subjectId"
        params={{ subjectId: item.subject_id }}
        search={{ tab: 'events', event_id: undefined }}
        className="text-primary hover:underline font-medium"
      >
        {item.display_title}
      </Link>
    )
  }
  if (type === 'document') {
    return <span className="font-medium">{item.display_title}</span>
  }
  return <span className="font-medium">{item.display_title}</span>
}

function SearchPage() {
  const { q: initialQ, scope: initialScope } = Route.useSearch()
  const navigate = useNavigate()
  const [query, setQuery] = useState(initialQ)
  const [scope, setScope] = useState<string>(initialScope)

  useEffect(() => {
    setQuery(initialQ)
    setScope(initialScope)
  }, [initialQ, initialScope])

  const runSearch = useCallback(() => {
    navigate({
      to: '/search',
      search: { q: query.trim(), scope: scope || 'all' },
      replace: true,
    })
  }, [navigate, query, scope])

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['search', initialQ, initialScope],
    queryFn: async () => {
      const { data: res, error } = await timelineApi.search.query({
        q: initialQ,
        scope: (initialScope as 'all' | 'subjects' | 'events' | 'documents') || 'all',
        limit: 50,
      })
      if (error) throw new Error('Search failed')
      return res?.results ?? []
    },
    enabled: initialQ.length > 0,
  })

  const results = data ?? []
  const searching = isLoading || isFetching

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-foreground mb-2">Search</h1>
        <p className="text-muted-foreground text-sm">
          Search across subjects, events, and documents.
        </p>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 max-w-2xl">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && runSearch()}
            className="pl-9"
            aria-label="Search query"
          />
        </div>
        <SingleSelectCombobox
          value={scope}
          onValueChange={setScope}
          options={SCOPE_OPTIONS.map((opt) => ({ value: opt.value, label: opt.label }))}
          placeholder="Scope"
          className="w-full sm:w-[140px]"
        />
        <Button onClick={runSearch} disabled={!query.trim()}>
          Search
        </Button>
      </div>

      {initialQ.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Enter a query and choose a scope, then click Search to find subjects, events, or
          documents.
        </p>
      )}

      {initialQ.length > 0 && (
        <div className="min-h-[200px]">
          {searching ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <Loader2 className="w-8 h-8 animate-spin mr-2" />
              Searching…
            </div>
          ) : results.length === 0 ? (
            <p className="text-muted-foreground py-8">No results found.</p>
          ) : (
            <ul className="space-y-4">
              {results.map((item) => (
                <li
                  key={`${item.resource_type}-${item.id}`}
                  className="border border-border rounded-lg p-4 bg-card hover:bg-muted/30 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <span className="shrink-0 mt-0.5 text-muted-foreground">
                      {item.resource_type === 'subject' && <Users className="w-4 h-4" />}
                      {item.resource_type === 'event' && <Calendar className="w-4 h-4" />}
                      {item.resource_type === 'document' && <FileText className="w-4 h-4" />}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <ResultLink item={item} />
                        <span className="text-xs text-muted-foreground uppercase tracking-wide">
                          {item.resource_type}
                        </span>
                      </div>
                      {item.snippet && (
                        <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                          {item.snippet}
                        </p>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
