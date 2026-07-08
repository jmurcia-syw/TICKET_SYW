import { Button } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { useLocation, useNavigate } from 'react-router-dom'

export interface TicketNavOrigin {
  pathname: string
  label: string
}

/** "Volver" del detalle del ticket (US4): regresa al origen de navegación (Kanban, Tickets,
 * Panel de Asignación) leído de `location.state.from`; sin origen (acceso directo por URL),
 * cae al listado de Tickets por defecto (FR-013). */
export default function TicketBreadcrumb() {
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: TicketNavOrigin } | null)?.from

  return (
    <Button
      icon={<ArrowLeftOutlined />}
      onClick={() => navigate(from ? from.pathname : '/tickets')}
    >
      {from ? `Volver a ${from.label}` : 'Volver'}
    </Button>
  )
}
