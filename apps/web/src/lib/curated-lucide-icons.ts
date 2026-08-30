/**
 * Curated set of Lucide icon names for subject type (and similar) pickers.
 * Not hardcoded in forms: add/remove here to change the picker set.
 * Names must match lucide-react exports (PascalCase).
 */
import type { LucideIcon } from 'lucide-react'
import {
  Archive,
  Bookmark,
  Box,
  Briefcase,
  Building,
  Building2,
  Calendar,
  Car,
  CreditCard,
  File,
  FileText,
  Flag,
  Folder,
  FolderKanban,
  Heart,
  Inbox,
  Mail,
  MapPin,
  MessageSquare,
  Package,
  Phone,
  Plane,
  Send,
  Ship,
  ShoppingBag,
  ShoppingCart,
  Star,
  Tag,
  Truck,
  User,
  UserCircle,
  Users,
} from 'lucide-react'

export const CURATED_ICONS: Record<string, LucideIcon> = {
  User,
  Users,
  UserCircle,
  Building,
  Building2,
  Briefcase,
  ShoppingCart,
  ShoppingBag,
  Package,
  File,
  FileText,
  Folder,
  FolderKanban,
  Tag,
  Calendar,
  Mail,
  Phone,
  MapPin,
  CreditCard,
  Heart,
  Star,
  Flag,
  Bookmark,
  Box,
  Archive,
  Inbox,
  Send,
  MessageSquare,
  Truck,
  Plane,
  Ship,
  Car,
}

export const ICON_NAMES = Object.keys(CURATED_ICONS).sort()

export function getCuratedIcon(name: string): LucideIcon | null {
  if (!name) return null
  const key = name.trim()
  if (!key) return null
  return CURATED_ICONS[key] ?? null
}
