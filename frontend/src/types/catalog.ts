export type CatalogName = 'tools' | 'processes' | 'resolution-types'

export interface CatalogItem {
  id: string
  name: string
  active: boolean
}

export const CATALOG_LABELS: Record<CatalogName, string> = {
  tools: 'Herramientas',
  processes: 'Procesos',
  'resolution-types': 'Tipos de resolución',
}
