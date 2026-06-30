import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Role } from '../types/api'

interface AuthState {
  token: string | null
  role: Role | null
  email: string | null
  setAuth: (token: string, role: Role, email: string) => void
  logout: () => void
  isAuthenticated: () => boolean
  hasRole: (...roles: Role[]) => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      role: null,
      email: null,
      setAuth: (token, role, email) => set({ token, role, email }),
      logout: () => set({ token: null, role: null, email: null }),
      isAuthenticated: () => !!get().token,
      hasRole: (...roles) => {
        const role = get().role
        return role !== null && roles.includes(role)
      },
    }),
    { name: 'sywork-auth' }
  )
)
