import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
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

// OBS-0027 ("una sesión por navegador"): `sessionStorage` aísla la sesión por pestaña — ya no
// se sobrescribe entre pestañas del mismo navegador al recargar. El `BroadcastChannel` fuerza
// el logout de las demás pestañas cuando se detecta un login nuevo en cualquiera de ellas
// (no se entrega a la pestaña que emite el mensaje, solo a las demás — comportamiento nativo).
const authBroadcast = typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel('sywork-auth') : null

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      userId: null,
      email: null,
      username: null,
      role: null,
      permissions: [],
      setAuth: (token, user) => {
        set({
          token,
          userId: user.id,
          email: user.email,
          username: user.username,
          role: user.role,
          permissions: user.permissions,
        })
        authBroadcast?.postMessage({ type: 'login' })
      },
      logout: () => set({ token: null, userId: null, email: null, username: null, role: null, permissions: [] }),
      isAuthenticated: () => !!get().token,
      hasPermission: (module, action) => get().permissions.some(p => p.module === module && p.action === action),
    }),
    { name: 'sywork-auth', storage: createJSONStorage(() => sessionStorage) }
  )
)

if (authBroadcast) {
  authBroadcast.onmessage = (event: MessageEvent<{ type: string }>) => {
    if (event.data?.type === 'login') {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
  }
}
