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
  /** spec 038 US5: si es true, el backend envía un correo de bienvenida HTML con la contraseña
   * temporal y un enlace de cambio válido 30 min. Default false. */
  notify?: boolean
}

export interface UserCreateResponse {
  user: UserAdmin
  provisional_password: string
  /** spec 038 US5: true si `notify` era true y el correo se envió sin error. */
  notification_sent: boolean
}
