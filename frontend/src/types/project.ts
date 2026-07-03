export interface ProjectListItem {
  id: string
  client_id: string
  client_name: string | null
  name: string
  description: string | null
  overview: string | null
  sale_services_usd: number | null
  sale_licenses_usd: number | null
  sale_subscriptions_usd: number | null
  components_sold: string | null
  active: boolean
  start_date: string
  end_date_estimated: string | null
  created_at: string
}

export interface ProjectFormData {
  client_id: string
  name: string
  description?: string | null
  overview?: string | null
  sale_services_usd?: number | null
  sale_licenses_usd?: number | null
  sale_subscriptions_usd?: number | null
  components_sold?: string | null
  start_date: string
  end_date_estimated?: string | null
}
