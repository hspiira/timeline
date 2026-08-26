/**
 * Subject type → icon and Tailwind theme.
 * Prefer subject type config (Settings → Subject types) when available;
 * fall back to this static map for legacy/unconfigured types.
 */

import type { LucideIcon } from 'lucide-react'
import {
  Building2,
  FileText,
  FolderKanban,
  Package,
  ShoppingCart,
  Tag,
  User,
  Users,
} from 'lucide-react'
import { getCuratedIcon } from '@/lib/curated-lucide-icons'

export interface SubjectTypeTheme {
  icon: LucideIcon
  bgColor: string
  textColor: string
  borderColor: string
  /** For table type badge (e.g. SubjectsTable) */
  accent: string
  /** For grid card header gradient (e.g. SubjectsGrid) */
  headerBg: string
}

const iconMap: Record<string, SubjectTypeTheme> = {
  user: {
    icon: User,
    bgColor: 'bg-blue-100 dark:bg-blue-900/20',
    textColor: 'text-blue-600 dark:text-blue-400',
    borderColor: 'border-blue-200 dark:border-blue-800',
    accent: 'text-blue-700 dark:text-blue-300',
    headerBg:
      'bg-gradient-to-r from-blue-50/50 to-blue-100/30 dark:from-blue-950/20 dark:to-blue-900/10',
  },
  users: {
    icon: Users,
    bgColor: 'bg-blue-100 dark:bg-blue-900/20',
    textColor: 'text-blue-600 dark:text-blue-400',
    borderColor: 'border-blue-200 dark:border-blue-800',
    accent: 'text-blue-700 dark:text-blue-300',
    headerBg:
      'bg-gradient-to-r from-blue-50/50 to-blue-100/30 dark:from-blue-950/20 dark:to-blue-900/10',
  },
  customer: {
    icon: Building2,
    bgColor: 'bg-purple-100 dark:bg-purple-900/20',
    textColor: 'text-purple-600 dark:text-purple-400',
    borderColor: 'border-purple-200 dark:border-purple-800',
    accent: 'text-purple-700 dark:text-purple-300',
    headerBg:
      'bg-gradient-to-r from-purple-50/50 to-purple-100/30 dark:from-purple-950/20 dark:to-purple-900/10',
  },
  order: {
    icon: ShoppingCart,
    bgColor: 'bg-green-100 dark:bg-green-900/20',
    textColor: 'text-green-600 dark:text-green-400',
    borderColor: 'border-green-200 dark:border-green-800',
    accent: 'text-green-700 dark:text-green-300',
    headerBg:
      'bg-gradient-to-r from-green-50/50 to-green-100/30 dark:from-green-950/20 dark:to-green-900/10',
  },
  project: {
    icon: FolderKanban,
    bgColor: 'bg-orange-100 dark:bg-orange-900/20',
    textColor: 'text-orange-600 dark:text-orange-400',
    borderColor: 'border-orange-200 dark:border-orange-800',
    accent: 'text-orange-700 dark:text-orange-300',
    headerBg:
      'bg-gradient-to-r from-orange-50/50 to-orange-100/30 dark:from-orange-950/20 dark:to-orange-900/10',
  },
  invoice: {
    icon: FileText,
    bgColor: 'bg-amber-100 dark:bg-amber-900/20',
    textColor: 'text-amber-600 dark:text-amber-400',
    borderColor: 'border-amber-200 dark:border-amber-800',
    accent: 'text-amber-700 dark:text-amber-300',
    headerBg:
      'bg-gradient-to-r from-amber-50/50 to-amber-100/30 dark:from-amber-950/20 dark:to-amber-900/10',
  },
  shipment: {
    icon: Package,
    bgColor: 'bg-cyan-100 dark:bg-cyan-900/20',
    textColor: 'text-cyan-600 dark:text-cyan-400',
    borderColor: 'border-cyan-200 dark:border-cyan-800',
    accent: 'text-cyan-700 dark:text-cyan-300',
    headerBg:
      'bg-gradient-to-r from-cyan-50/50 to-cyan-100/30 dark:from-cyan-950/20 dark:to-cyan-900/10',
  },
  package: {
    icon: Package,
    bgColor: 'bg-cyan-100 dark:bg-cyan-900/20',
    textColor: 'text-cyan-600 dark:text-cyan-400',
    borderColor: 'border-cyan-200 dark:border-cyan-800',
    accent: 'text-cyan-700 dark:text-cyan-300',
    headerBg:
      'bg-gradient-to-r from-cyan-50/50 to-cyan-100/30 dark:from-cyan-950/20 dark:to-cyan-900/10',
  },
}

const defaultTheme: SubjectTypeTheme = {
  icon: Tag,
  bgColor: 'bg-gray-100 dark:bg-gray-900/20',
  textColor: 'text-gray-600 dark:text-gray-400',
  borderColor: 'border-gray-200 dark:border-gray-800',
  accent: 'text-gray-700 dark:text-gray-300',
  headerBg:
    'bg-gradient-to-r from-gray-50/50 to-gray-100/30 dark:from-gray-950/20 dark:to-gray-900/10',
}

export function getSubjectTypeTheme(subjectType: string): SubjectTypeTheme {
  return iconMap[subjectType.toLowerCase()] ?? defaultTheme
}

/** Config item from API (Subject types list); has icon name and optional hex color. */
export interface SubjectTypeConfigItem {
  type_name: string
  display_name?: string | null
  icon?: string | null
  color?: string | null
}

export interface SubjectTypeThemeFromConfig extends SubjectTypeTheme {
  /** When set, use this hex for bg/border instead of theme Tailwind classes (from subject type config). */
  configColor?: string | null
}

/**
 * Resolve icon and theme for a subject type. Prefers subject type config (API) over the static theme map.
 * Use this in subject list/grid/detail so configured types show their chosen icon and color.
 */
export function getSubjectTypeThemeFromConfig(
  subjectType: string,
  config?: SubjectTypeConfigItem[] | null,
): SubjectTypeThemeFromConfig {
  const theme = getSubjectTypeTheme(subjectType)
  if (!config?.length) return { ...theme, configColor: null }

  const found = config.find((t) => t.type_name.toLowerCase() === subjectType.toLowerCase())
  if (!found) return { ...theme, configColor: null }

  const iconFromConfig = found.icon?.trim()
  const configIcon = iconFromConfig ? getCuratedIcon(iconFromConfig) : null
  return {
    ...theme,
    icon: configIcon ?? theme.icon,
    configColor: found.color?.trim() || null,
  }
}
