import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronDown } from 'lucide-react'
import { timelineApi } from '@/lib/api-client'
import { getTenantId, setTenantId } from '@/lib/api-client'
import { authActions } from '@/lib/auth-store'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'

export function TenantSelector() {
  const queryClient = useQueryClient()
  const currentId = getTenantId()

  const { data: tenants, isLoading } = useQuery({
    queryKey: ['tenants'],
    queryFn: async () => {
      const res = await timelineApi.tenants.list()
      if (res.error || !res.data) return []
      return res.data
    },
  })

  const current = tenants?.find((t) => t.id === currentId)
  const displayName = current?.name ?? current?.code ?? currentId ?? 'Tenant'

  const handleSelect = async (tenantId: string) => {
    if (tenantId === currentId) return
    setTenantId(tenantId)
    queryClient.clear()
    await authActions.initAuth()
  }

  if (isLoading || !tenants?.length) {
    return (
      <span className="text-sm font-medium text-muted-foreground px-3 py-2">
        {displayName}
      </span>
    )
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="gap-1 font-medium text-foreground/90 hover:text-foreground"
        >
          {displayName}
          <ChevronDown className="w-4 h-4 opacity-70" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        {tenants.map((t) => (
          <DropdownMenuItem
            key={t.id}
            onClick={() => handleSelect(t.id)}
            className={t.id === currentId ? 'bg-accent' : ''}
          >
            {t.name || t.code}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
