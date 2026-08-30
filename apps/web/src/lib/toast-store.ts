import { Store } from '@tanstack/store'

export interface ToastItem {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message?: string
  duration?: number
}

interface ToastState {
  toasts: ToastItem[]
}

let toastId = 0

const initialState: ToastState = {
  toasts: [],
}

export const toastStore = new Store(initialState)

// Helper functions
export const addToast = (toast: Omit<ToastItem, 'id'>) => {
  const id = `toast-${++toastId}`
  toastStore.setState((state) => ({
    toasts: [...state.toasts, { ...toast, id }],
  }))
}

export const removeToast = (id: string) => {
  toastStore.setState((state) => ({
    toasts: state.toasts.filter((t) => t.id !== id),
  }))
}

export const clearAllToasts = () => {
  toastStore.setState({ toasts: [] })
}
