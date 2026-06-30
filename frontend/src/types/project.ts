export interface ProjectListItem {
  id: string
  client_id: string
  client_name: string | null
  name: string
  description: string | null
  active: boolean
  start_date: string
  end_date_estimated: string | null
  created_at: string
}

export interface ProjectFormData {
  client_id: string
  name: string
  description?: string
  start_date: string
  end_date_estimated?: string
}
