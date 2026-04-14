import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import type { UserRole } from '../contexts/AuthContext'

export function ProtectedRoute({
  children,
  allowedRoles,
}: {
  children: React.ReactNode
  allowedRoles?: UserRole[]
}) {
  const { user } = useAuth()
  const loc = useLocation()
  if (!user) {
    return <Navigate to="/login" replace state={{ from: loc.pathname }} />
  }

  if (allowedRoles && allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
    return <Navigate to="/browse" replace />
  }
  return <>{children}</>
}
