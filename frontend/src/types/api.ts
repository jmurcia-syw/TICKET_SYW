export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface ApiError {
  error: string
  message: string
}

export type Role = 'admin' | 'coordinator' | 'qm' | 'resolver'

export type ActiveStatus = 'active' | 'inactive'
