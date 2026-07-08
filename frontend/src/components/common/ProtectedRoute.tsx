import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'

interface Props {
  children: ReactNode
  /** `action` acepta una sola acción o una lista de alternativas (cualquiera habilita el
   * acceso) — ej. Tickets: `['view', 'view_own']` para Coordinador/Resolutor vs Encargado. */
  requiredPermission?: { module: string; action: string | string[] }
}

export default function ProtectedRoute({ children, requiredPermission }: Props) {
  const { isAuthenticated, hasPermission } = useAuthStore()

  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />
  }

  if (requiredPermission) {
    const actions = Array.isArray(requiredPermission.action) ? requiredPermission.action : [requiredPermission.action]
    if (!actions.some(action => hasPermission(requiredPermission.module, action))) {
      return <Navigate to="/dashboard" replace />
    }
  }

  return <>{children}</>
}
