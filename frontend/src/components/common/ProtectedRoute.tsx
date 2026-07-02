import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'

interface Props {
  children: ReactNode
  requiredPermission?: { module: string; action: string }
}

export default function ProtectedRoute({ children, requiredPermission }: Props) {
  const { isAuthenticated, hasPermission } = useAuthStore()

  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />
  }

  if (requiredPermission && !hasPermission(requiredPermission.module, requiredPermission.action)) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}
