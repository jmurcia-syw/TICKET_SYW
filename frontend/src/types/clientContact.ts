export interface ContactProjectRef {
  id: string
  name: string
}

export interface ClientContact {
  id: string
  user_id: string
  client_id: string
  email: string
  username: string
  client_name: string
  /** Proyectos vinculados vía personal del proyecto (spec 010). */
  projects: ContactProjectRef[]
  created_at: string
}

/** Alta por Proyecto (spec 010: el Cliente se deriva del proyecto y la membresía se crea
 * automáticamente). `client_id` directo es la forma legada (spec 007). */
export interface ClientContactCreateRequest {
  email: string
  username: string
  project_id?: string
  client_id?: string
}

export interface ClientContactCreateResponse {
  id: string
  user_id: string
  client_id: string
  email: string
  client_name: string
  provisional_password: string
}
