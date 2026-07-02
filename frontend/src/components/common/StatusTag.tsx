import { Tag } from 'antd'
import { STATUS_COLORS } from '../../theme'

export default function StatusTag({ active }: { active: boolean }) {
  return <Tag color={active ? STATUS_COLORS.active : STATUS_COLORS.inactive}>{active ? 'Activo' : 'Inactivo'}</Tag>
}
