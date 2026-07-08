export interface ClientContact {
  id: string
  user_id: string
  client_id: string
  email: string
  username: string
  client_name: string
  created_at: string
}

export interface ClientContactCreateRequest {
  email: string
  username: string
  client_id: string
}

export interface ClientContactCreateResponse {
  id: string
  user_id: string
  client_id: string
  email: string
  client_name: string
  provisional_password: string
}
