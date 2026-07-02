import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Permission, Role } from '../types/api'

export interface AuthUser {
  id: string
  email: string
  username: string
  role: Role
  permissions: Permission[]
}

interface AuthState {
  token: string | null
  userId: string | null
  email: string | null
  username: string | null
  role: Role | null
  permissions: Permission[]
  setAuth: (token: string, user: AuthUser) => void
  logout: () => void
  isAuthenticated: () => boolean
  hasPermission: (module: string, action: string) => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      userId: null,
      email: null,
      username: null,
      role: null,
      permissions: [],
      setAuth: (token, user) =>
        set({
          token,
          userId: user.id,
          email: user.email,
          username: user.username,
          role: user.role,
          permissions: user.permissions,
        }),
      logout: () => set({ token: null, userId: null, email: null, username: null, role: null, permissions: [] }),
      isAuthenticated: () => !!get().token,
      hasPermission: (module, action) => get().permissions.some(p => p.module === module && p.action === action),
    }),
    { name: 'sywork-auth' }
  )
)
