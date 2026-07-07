import { Button, Input, Space } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import type { ColumnType } from 'antd/es/table'
import { vivid } from '../../theme'

/**
 * Filtro de texto para el header de columna (icono de lupa + input + Buscar/Limpiar).
 * Delegado a un setter externo: reutiliza el mismo estado que ya dispara la búsqueda
 * server-side de la página (o filtra en memoria si se le pasa un setter local), en vez
 * de duplicar la lógica de filtrado por columna.
 */
export function textColumnFilter<T>(
  placeholder: string,
  value: string,
  onChange: (value: string) => void,
): Partial<ColumnType<T>> {
  return {
    filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters, close }) => (
      <div style={{ padding: 8 }} onKeyDown={e => e.stopPropagation()}>
        <Input
          autoFocus
          placeholder={placeholder}
          value={(selectedKeys[0] as string) ?? ''}
          onChange={e => setSelectedKeys(e.target.value ? [e.target.value] : [])}
          onPressEnter={() => { onChange((selectedKeys[0] as string) ?? ''); confirm() }}
          style={{ display: 'block', marginBottom: 8, width: 200 }}
        />
        <Space>
          <Button type="primary" size="small" style={{ width: 90 }}
            onClick={() => { onChange((selectedKeys[0] as string) ?? ''); confirm() }}>
            Buscar
          </Button>
          <Button size="small" style={{ width: 90 }}
            onClick={() => { clearFilters?.(); onChange(''); close() }}>
            Limpiar
          </Button>
        </Space>
      </div>
    ),
    filterIcon: (filtered: boolean) => (
      <SearchOutlined style={{ color: filtered || value ? vivid.blue.text : undefined }} />
    ),
    filteredValue: value ? [value] : null,
    onFilter: () => true,
  }
}

/**
 * Filtro de checklist (single-select) para el header de columna, delegado a un
 * setter externo que dispara el refetch server-side (ej. estado activo/inactivo, rol).
 */
export function serverColumnFilter<T>(
  options: { text: string; value: string }[],
  value: string | undefined,
): Partial<ColumnType<T>> {
  return {
    filters: options,
    filterMultiple: false,
    filteredValue: value ? [value] : null,
    onFilter: () => true,
  }
}

/**
 * Filtro de checklist (single-select) 100% cliente: para grids cuyo dataSource ya
 * contiene el universo completo de filas (sin paginación server-side), donde no hace
 * falta refetch — antd filtra directamente sobre las filas cargadas.
 */
export function clientColumnFilter<T>(
  options: { text: string; value: string }[],
  onFilter: (value: string, record: T) => boolean,
): Partial<ColumnType<T>> {
  return {
    filters: options,
    filterMultiple: false,
    onFilter: (value, record) => onFilter(String(value), record),
  }
}

/**
 * Filtro de búsqueda de texto 100% cliente (sin estado externo): para grids cuyo
 * dataSource ya contiene el universo completo de filas. `getText` extrae el campo a
 * comparar de cada fila.
 */
export function clientTextColumnFilter<T>(
  placeholder: string,
  getText: (record: T) => string,
): Partial<ColumnType<T>> {
  return {
    filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters, close }) => (
      <div style={{ padding: 8 }} onKeyDown={e => e.stopPropagation()}>
        <Input
          autoFocus
          placeholder={placeholder}
          value={(selectedKeys[0] as string) ?? ''}
          onChange={e => setSelectedKeys(e.target.value ? [e.target.value] : [])}
          onPressEnter={() => confirm()}
          style={{ display: 'block', marginBottom: 8, width: 200 }}
        />
        <Space>
          <Button type="primary" size="small" style={{ width: 90 }} onClick={() => confirm()}>
            Buscar
          </Button>
          <Button size="small" style={{ width: 90 }}
            onClick={() => { clearFilters?.(); close() }}>
            Limpiar
          </Button>
        </Space>
      </div>
    ),
    filterIcon: (filtered: boolean) => (
      <SearchOutlined style={{ color: filtered ? vivid.blue.text : undefined }} />
    ),
    onFilter: (value, record) => getText(record).toLowerCase().includes(String(value).toLowerCase()),
  }
}
