import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'

interface Props {
  children: ReactNode
  /** `action` acepta una sola acción o una lista de alternativas (cualquiera habilita el
   * acceso) — ej. Tickets: `['view', 'view_own']` para Coordinador/Resolutor vs Usuario/cliente. */
  requiredPermission?: { module: string; action: string | string[] }
  /** FR-006 (spec 038, US1): bloquea el acceso directo por URL a un catálogo maestro
   * administrativo para roles específicos, aunque conserven el permiso `view` del módulo
   * (lo necesitan para selects acotados puntuales, no para navegar la pantalla completa). */
  blockRoles?: string[]
}

export default function ProtectedRoute({ children, requiredPermission, blockRoles }: Props) {
  const { isAuthenticated, hasPermission, role } = useAuthStore()

  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />
  }

  if (blockRoles && role?.name && blockRoles.includes(role.name)) {
    return <Navigate to="/dashboard" replace />
  }

  if (requiredPermission) {
    const actions = Array.isArray(requiredPermission.action) ? requiredPermission.action : [requiredPermission.action]
    if (!actions.some(action => hasPermission(requiredPermission.module, action))) {
      return <Navigate to="/dashboard" replace />
    }
  }

  return <>{children}</>
}
