export type SkillType = 'funcional' | 'tecnico'

export interface Skill {
  id: string
  code: string
  label: string
  active?: boolean
  skill_type?: SkillType
  tool_id?: string | null
  tool_name?: string | null
  process_id?: string | null
  process_name?: string | null
}

export interface Resource {
  id: string
  user_id: string | null
  full_name: string
  email: string
  active: boolean
  notes: string | null
  identification: string | null
  nationality: string | null
  birth_date: string | null
  marital_status: string | null
  contract_type: string | null
  calendar_country: string | null
  education_level: string | null
  specialty: string | null
  seniority: string | null
  certifications: string | null
  team: string | null
  manager_id: string | null
  /** Huso horario IANA del recurso (Fase 5), ej. "America/Bogota". */
  timezone: string | null
  skills: Skill[]
  created_at: string
}

export interface ResourceFormData {
  full_name: string
  email: string
  user_id?: string | null
  skill_ids?: string[]
  notes?: string | null
  identification?: string | null
  nationality?: string | null
  birth_date?: string | null
  marital_status?: string | null
  contract_type?: string | null
  calendar_country?: string | null
  education_level?: string | null
  specialty?: string | null
  seniority?: string | null
  certifications?: string | null
  team?: string | null
  manager_id?: string | null
  timezone?: string | null
}

export interface ResourceCompensation {
  resource_id: string
  base_salary: number | null
  total_salary: number | null
  overhead: number | null
  hourly_cost: number | null
  currency: string
  updated_at: string | null
}

export interface CompensationFormData {
  base_salary?: number | null
  total_salary?: number | null
  overhead?: number | null
  currency?: string
}
