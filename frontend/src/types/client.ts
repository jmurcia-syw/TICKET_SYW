export interface ClientListItem {
  id: string
  name: string
  slug: string
  active: boolean
  contact_name: string | null
  contact_email: string | null
  contact_phone: string | null
  annual_billing_usd: number | null
  created_at: string
  updated_at: string
}

export interface ClientDetail extends ClientListItem {
  notes: string | null
}

export interface ClientFormData {
  name: string
  contact_name?: string | null
  contact_email?: string | null
  contact_phone?: string | null
  annual_billing_usd?: number | null
  notes?: string | null
}

export interface ClientSystem {
  id: string
  client_id: string
  system_type: string
  brand: string
  version: string | null
  notes: string | null
  created_at: string
}

export interface ClientSystemFormData {
  system_type: string
  brand: string
  version?: string | null
  notes?: string | null
}

export type ClientAccessType = 'vpn' | 'system_url' | 'remote_desktop'
export type ClientAccessEnvironment = 'dev' | 'test' | 'prod'

export interface ClientAccess {
  id: string
  client_id: string
  access_type: ClientAccessType
  environment: ClientAccessEnvironment | null
  username: string | null
  password: string | null
  host: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface ClientAccessFormData {
  access_type: ClientAccessType
  environment?: ClientAccessEnvironment | null
  username?: string | null
  password?: string | null
  host?: string | null
  notes?: string | null
}

export interface ClientAccessAttachment {
  id: string
  client_id: string
  filename: string
  content_type: string
  size_bytes: number
  created_at: string
}
