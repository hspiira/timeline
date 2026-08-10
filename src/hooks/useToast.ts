import { addToast, ToastItem } from '@/lib/toast-store'

export function useToast() {
  return {
    success: (title: string, message?: string) =>
      addToast({ type: 'success', title, message, duration: 3000 }),
    error: (title: string, message?: string) =>
      addToast({ type: 'error', title, message, duration: 5000 }),
    warning: (title: string, message?: string) =>
      addToast({ type: 'warning', title, message, duration: 4000 }),
    info: (title: string, message?: string) =>
      addToast({ type: 'info', title, message, duration: 3000 }),
    custom: (toast: Omit<ToastItem, 'id'>) => addToast(toast),
  }
}
