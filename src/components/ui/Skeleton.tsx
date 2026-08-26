interface SkeletonProps {
  className?: string
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return <div className={`bg-muted animate-pulse rounded-none ${className}`} />
}

export function SkeletonText() {
  return <Skeleton className="h-4 w-full" />
}

export function SkeletonHeading() {
  return <Skeleton className="h-8 w-3/4" />
}

export function SkeletonCard() {
  return (
    <div className="bg-card/80 backdrop-blur-sm rounded-none p-4 border border-border/50">
      <Skeleton className="h-6 w-1/3 mb-4" />
      <div className="space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-4/6" />
      </div>
    </div>
  )
}

export function SkeletonEventCard() {
  return (
    <div className="bg-card/80 backdrop-blur-sm rounded-none p-3 border border-border/50">
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <Skeleton className="h-5 w-1/2 mb-2" />
          <Skeleton className="h-4 w-1/3" />
        </div>
        <Skeleton className="h-6 w-16" />
      </div>
      <Skeleton className="h-3 w-1/4 mt-3" />
    </div>
  )
}

export function SkeletonEventTimeline() {
  return (
    <div className="space-y-6">
      {/* Date header */}
      <div>
        <Skeleton className="h-5 w-1/4 mb-4" />
        {/* Event cards */}
        <div className="ml-6 space-y-2">
          <SkeletonEventCard />
          <SkeletonEventCard />
          <SkeletonEventCard />
        </div>
      </div>
    </div>
  )
}

export function SkeletonBreadcrumbs() {
  return (
    <div className="flex items-center gap-2 mb-4">
      <Skeleton className="h-4 w-20" />
      <Skeleton className="h-4 w-4" />
      <Skeleton className="h-4 w-24" />
    </div>
  )
}

export function SkeletonDocumentItem() {
  return (
    <div className="flex items-center justify-between p-3 border border-border/50 rounded-none bg-card/40">
      <div className="flex items-center gap-3 flex-1">
        <Skeleton className="h-5 w-5" />
        <div className="flex-1">
          <Skeleton className="h-4 w-1/2 mb-1" />
          <Skeleton className="h-3 w-1/3" />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Skeleton className="h-8 w-8" />
        <Skeleton className="h-8 w-8" />
      </div>
    </div>
  )
}

export function SkeletonDocumentList() {
  return (
    <div className="space-y-2">
      <SkeletonDocumentItem />
      <SkeletonDocumentItem />
      <SkeletonDocumentItem />
      <SkeletonDocumentItem />
    </div>
  )
}
