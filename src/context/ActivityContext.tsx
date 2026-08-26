import React, { createContext, type ReactNode, useCallback, useState } from 'react'

interface ActivityContextType {
  selected: string | null
  setSelected: (id: string | null) => void
  expanded: Set<string>
  toggleExpanded: (id: string) => void
  expandAll: () => void
  collapseAll: () => void
  hoveredId: string | null
  setHoveredId: (id: string | null) => void
}

export const ActivityContext = createContext<ActivityContextType | null>(null)

export function ActivityProvider({ children }: { children: ReactNode }) {
  const [selected, setSelected] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  const toggleExpanded = useCallback((id: string) => {
    setExpanded((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return newSet
    })
  }, [])

  const expandAll = useCallback(() => {
    // Will be used with a set of activities
    // This is a placeholder - caller will pass activity IDs
  }, [])

  const collapseAll = useCallback(() => {
    setExpanded(new Set())
  }, [])

  const value: ActivityContextType = {
    selected,
    setSelected,
    expanded,
    toggleExpanded,
    expandAll,
    collapseAll,
    hoveredId,
    setHoveredId,
  }

  return <ActivityContext.Provider value={value}>{children}</ActivityContext.Provider>
}

export function useActivityContext() {
  const context = React.useContext(ActivityContext)
  if (!context) {
    throw new Error('useActivityContext must be used within ActivityProvider')
  }
  return context
}
