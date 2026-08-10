import { useStore } from '@tanstack/react-store'
import { Toast, ToastType } from './Toast'
import { toastStore, removeToast } from '@/lib/toast-store'

export function ToastContainer() {
  const state = useStore(toastStore)
  const toasts = state.toasts

  return (
    <div className="fixed top-4 right-4 z-[9999] pointer-events-none">
      <div className="flex flex-col gap-2 max-w-sm pointer-events-auto">
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            id={toast.id}
            type={toast.type as ToastType}
            title={toast.title}
            message={toast.message}
            duration={toast.duration}
            onClose={removeToast}
          />
        ))}
      </div>
    </div>
  )
}
