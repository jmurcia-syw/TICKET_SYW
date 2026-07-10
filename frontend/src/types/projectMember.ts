export interface ProjectMember {
  id: string
  project_id: string
  user_id: string
  full_name: string | null
  email: string | null
  role_name: string | null
  assigned_at: string | null
}

export interface ProjectTeamMember {
  member_id: string
  user_id: string
  full_name: string | null
  email: string | null
  role_name: string | null
}

export interface ProjectTeam {
  id: string
  project_id: string
  name: string
  members: ProjectTeamMember[]
  member_count: number
  created_at: string | null
}
