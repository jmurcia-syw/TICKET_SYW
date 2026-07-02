import type { Role } from './api'

export interface UserAdmin {
  id: string
  email: string
  username: string
  role: Role
  active: boolean
  last_login_at: string | null
  created_at: string
}

export interface RoleChangeRequest {
  role_id: string
}

export interface UserCreateRequest {
  email: string
  username: string
  role_id: string
}

export interface UserCreateResponse {
  user: UserAdmin
  provisional_password: string
}
