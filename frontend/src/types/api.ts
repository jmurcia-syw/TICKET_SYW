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

export interface Role {
  id: string
  name: string
}

export interface Permission {
  module: string
  action: string
}

export type ActiveStatus = 'active' | 'inactive'
