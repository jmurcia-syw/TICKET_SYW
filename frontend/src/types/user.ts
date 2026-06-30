import type { Role } from './api'

export interface UserAdmin {
  id: string
  email: string
  role: Role
  active: boolean
  last_login_at: string | null
  created_at: string
}

export interface RoleChangeRequest {
  role: Role
}
