import { Search, X } from 'lucide-react'
import { useDebouncedSearch } from '@/hooks/useDebouncedSearch'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { LoadingIcon } from '@/components/ui/icons'

interface ActivitySearchBarProps {
  onSearch: (query: string) => void
  placeholder?: string
  delay?: number
}

/**
 * Search bar component for activity filtering
 * Features debounced search to avoid excessive filtering
 */
export function ActivitySearchBar({
  onSearch,
  placeholder = 'Search activities by name, ID, or description...',
  delay = 300,
}: ActivitySearchBarProps) {
  const { query, setQuery, isSearching, clearSearch } = useDebouncedSearch({
    delay,
    onSearch,
  })

  return (
    <div className="relative w-full">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 w-4 h-4 transform -translate-y-1/2 text-muted-foreground pointer-events-none z-10" />
        <Input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder={placeholder}
          className="pl-10 pr-10"
          helperText={query && !isSearching ? `Showing results for "${query}"` : undefined}
        />
        {query && (
          isSearching ? (
            <div className="absolute right-3 top-2.5 z-10">
              <LoadingIcon className="text-muted-foreground" />
            </div>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearSearch}
              className="absolute right-3 top-2 p-1 h-auto z-10"
              aria-label="Clear search"
            >
              <X className="w-4 h-4" />
            </Button>
          )
        )}
      </div>
    </div>
  )
}

export default ActivitySearchBar
