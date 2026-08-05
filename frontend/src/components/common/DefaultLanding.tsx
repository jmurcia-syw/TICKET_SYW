import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'

/** Redirección por defecto al entrar a `/` o `/dashboard` — antes apuntaba fijo a `/tickets`,
 * lo que dejaba a un Resolutor (spec 038, US1: pierde `tickets:view`/`view_own`, solo conserva
 * `tickets:view_assigned`) en un loop de redirección contra `ProtectedRoute` (`/tickets` deniega
 * -> `/dashboard` -> `/tickets` ...). Elige el primer destino accesible según los permisos reales
 * del actor; `/me` (perfil propio) no tiene gate de permiso y es el último recurso. */
export default function DefaultLanding() {
  const { hasPermission } = useAuthStore()
  if (hasPermission('tickets', 'view') || hasPermission('tickets', 'view_own')) {
    return <Navigate to="/tickets" replace />
  }
  if (hasPermission('tickets', 'view_assigned')) {
    return <Navigate to="/my-tasks" replace />
  }
  if (hasPermission('work_sessions', 'view_own')) {
    return <Navigate to="/registro-tiempos" replace />
  }
  return <Navigate to="/me" replace />
}
