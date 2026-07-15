import { Tag } from 'antd'
import { SortDescendingOutlined } from '@ant-design/icons'
import { palette } from '../../theme'

/** OBS-0028: indicador visual del criterio de orden activo (por ahora fijo — el
 * default 'urgency' de la API no es configurable desde la UI todavía). */
export default function SortIndicator() {
  return (
    <Tag icon={<SortDescendingOutlined />} color="default" style={{ color: palette.slate600, borderColor: palette.slate200 }}>
      Ordenado por: Prioridad
    </Tag>
  )
}
