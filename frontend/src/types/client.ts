export interface ClientListItem {
  id: string
  name: string
  slug: string
  active: boolean
  contact_name: string | null
  contact_email: string | null
  contact_phone: string | null
  created_at: string
  updated_at: string
}

export interface ClientDetail extends ClientListItem {
  vpn_ips: string | null
  vpn_credentials: string | null
  notes: string | null
}

export interface ClientFormData {
  name: string
  contact_name?: string
  contact_email?: string
  contact_phone?: string
  vpn_ips?: string
  vpn_credentials?: string
  notes?: string
}
