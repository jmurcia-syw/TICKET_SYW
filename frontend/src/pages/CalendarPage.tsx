import { useEffect, useMemo, useState } from 'react'
import { Empty, Select, Space, Tabs, Typography, message } from 'antd'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import { calendarService } from '../services/calendarService'
import { clientService } from '../services/clientService'
import { resourceService } from '../services/resourceService'
import type { ClientListItem } from '../types/client'
import type { Resource } from '../types/resource'
import type { Holiday } from '../types/calendar'

// Fase 5 (spec 020, Historia 3): calendario de festivos por país — pestaña "Cliente" (un
// calendario para el país del cliente elegido) y "Equipo" (un calendario por cada miembro
// seleccionado, cada uno en el país de su propio `calendar_country`, sin mezclar festivos entre
// ellos — FR-001/002/004/005).

function HolidayCalendar({ country, title }: { country: string | null; title: string }) {
  const [holidays, setHolidays] = useState<Holiday[]>([])

  useEffect(() => {
    if (!country) {
      setHolidays([])
      return
    }
    calendarService.listHolidays(country).then(setHolidays)
      .catch(() => message.error(`No se pudieron cargar los festivos de ${country}`))
  }, [country])

  const events = useMemo(() => holidays.map(h => ({
    title: h.name, start: h.holiday_date, allDay: true, color: '#fa8c16',
  })), [holidays])

  return (
    <div style={{ border: '1px solid #f0f0f0', borderRadius: 8, padding: 12 }}>
      <Typography.Text strong style={{ display: 'block', marginBottom: 8 }}>{title}</Typography.Text>
      {!country
        ? <Empty description="Sin país configurado — no hay festivos que mostrar" style={{ margin: '24px 0' }} />
        : <FullCalendar
            key={country}
            plugins={[dayGridPlugin]}
            initialView="dayGridMonth"
            height="auto"
            headerToolbar={{ left: 'prev,next today', center: 'title', right: '' }}
            events={events}
            locale="es"
          />}
    </div>
  )
}

export default function CalendarPage() {
  const [clients, setClients] = useState<ClientListItem[]>([])
  const [selectedClientId, setSelectedClientId] = useState<string>()
  const [resources, setResources] = useState<Resource[]>([])
  const [selectedResourceIds, setSelectedResourceIds] = useState<string[]>([])

  useEffect(() => {
    clientService.list({ active: true, page_size: 200 }).then(r => setClients(r.items))
      .catch(() => message.error('No se pudo cargar la lista de clientes'))
    resourceService.list({ active: true, page_size: 200 }).then(r => setResources(r.items))
      .catch(() => message.error('No se pudo cargar la lista de recursos'))
  }, [])

  const selectedClient = clients.find(c => c.id === selectedClientId)
  const selectedResources = resources.filter(r => selectedResourceIds.includes(r.id))

  const tabs = [
    {
      key: 'client',
      label: 'Cliente',
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size={16}>
          <Select
            placeholder="Selecciona un cliente" showSearch optionFilterProp="label" allowClear
            style={{ width: 320 }} value={selectedClientId} onChange={setSelectedClientId}
            options={clients.map(c => ({ value: c.id, label: c.name }))}
          />
          {selectedClientId
            ? <HolidayCalendar country={selectedClient?.country ?? null} title={selectedClient?.name ?? ''} />
            : <Typography.Text type="secondary">Selecciona un cliente para ver su calendario de festivos.</Typography.Text>}
        </Space>
      ),
    },
    {
      key: 'team',
      label: 'Equipo',
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size={16}>
          <Select
            mode="multiple" placeholder="Selecciona miembros del equipo" showSearch optionFilterProp="label"
            style={{ width: '100%' }} value={selectedResourceIds} onChange={setSelectedResourceIds}
            options={resources.map(r => ({ value: r.id, label: r.full_name }))}
          />
          {selectedResources.length === 0
            ? <Typography.Text type="secondary">Selecciona uno o más miembros del equipo.</Typography.Text>
            : <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>
                {selectedResources.map(r => (
                  <HolidayCalendar key={r.id} country={r.calendar_country} title={r.full_name} />
                ))}
              </div>}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Typography.Title level={4}>Calendarios</Typography.Title>
      <Tabs items={tabs} />
    </div>
  )
}
