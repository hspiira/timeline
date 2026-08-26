import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from 'lucide-react'
import { useEffect } from 'react'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface ToastProps {
  id: string
  type: ToastType
  title: string
  message?: string
  duration?: number
  onClose: (id: string) => void
}

const toastStyles = {
  success: {
    bg: 'bg-emerald-50 dark:bg-emerald-950/50',
    border: 'border-emerald-200 dark:border-emerald-700',
    icon: 'text-emerald-600 dark:text-emerald-300',
    title: 'text-emerald-900 dark:text-emerald-100',
    message: 'text-emerald-800 dark:text-emerald-200',
  },
  error: {
    bg: 'bg-red-50 dark:bg-red-950/50',
    border: 'border-red-200 dark:border-red-700',
    icon: 'text-red-600 dark:text-red-300',
    title: 'text-red-900 dark:text-red-100',
    message: 'text-red-800 dark:text-red-200',
  },
  warning: {
    bg: 'bg-amber-50 dark:bg-amber-950/50',
    border: 'border-amber-200 dark:border-amber-700',
    icon: 'text-amber-600 dark:text-amber-300',
    title: 'text-amber-900 dark:text-amber-100',
    message: 'text-amber-800 dark:text-amber-200',
  },
  info: {
    bg: 'bg-blue-50 dark:bg-blue-950/50',
    border: 'border-blue-200 dark:border-blue-700',
    icon: 'text-blue-600 dark:text-blue-300',
    title: 'text-blue-900 dark:text-blue-100',
    message: 'text-blue-800 dark:text-blue-200',
  },
}

const toastIcons = {
  success: CheckCircle2,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
}

export function Toast({ id, type, title, message, duration = 4000, onClose }: ToastProps) {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => onClose(id), duration)
      return () => clearTimeout(timer)
    }
  }, [id, duration, onClose])

  const styles = toastStyles[type]
  const Icon = toastIcons[type]

  return (
    <div
      className={`${styles.bg} border ${styles.border} rounded-none p-4 flex gap-3 items-start shadow-lg animate-in fade-in slide-in-from-top-2 duration-200`}
      role="alert"
    >
      <Icon className={`w-5 h-5 ${styles.icon} flex-shrink-0 mt-0.5`} />
      <div className="flex-1">
        <p className={`font-semibold text-sm ${styles.title}`}>{title}</p>
        {message && <p className={`text-sm mt-0.5 ${styles.message}`}>{message}</p>}
      </div>
      <button
        onClick={() => onClose(id)}
        className={`flex-shrink-0 ${styles.icon} hover:opacity-70 transition-opacity`}
        aria-label="Close notification"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}
