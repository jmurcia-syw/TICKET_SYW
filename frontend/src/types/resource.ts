export interface Skill {
  id: string
  code: string
  label: string
  active?: boolean
}

export interface Resource {
  id: string
  user_id: string | null
  full_name: string
  email: string
  active: boolean
  notes: string | null
  skills: Skill[]
  created_at: string
}

export interface ResourceFormData {
  full_name: string
  email: string
  user_id?: string
  skill_ids?: string[]
  notes?: string
}
