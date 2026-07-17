import { useEffect, useMemo, useState } from 'react'
import { Button, Card, Empty, Select, Space, Statistic, Tabs, Typography, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import { calendarService } from '../services/calendarService'
import { clientService } from '../services/clientService'
import { resourceService } from '../services/resourceService'
import { avatarColor, CALENDAR_CATEGORY_COLORS } from '../theme'
import type { ClientListItem } from '../types/client'
import type { Resource } from '../types/resource'
import type { Holiday, Workload } from '../types/calendar'
import AbsenceRequestFormModal from '../components/calendar/AbsenceRequestFormModal'
import DayAgenda from '../components/calendar/DayAgenda'

// Fase 5 (spec 020, Historia 3): calendario de festivos por país — pestaña "Cliente" (un
// calendario para el país del cliente elegido) y "Equipo" (superposición real de varios
// miembros en una sola vista — spec 022, Historia 3, FR-011 a FR-014).
// Spec 021: categoría Oficial (teal) vs. Regional/Religioso (violeta), + cumpleaños del
// recurso (lima, solo en la pestaña Equipo — FR-005 a FR-014). Colores en theme.ts
// (CALENDAR_CATEGORY_COLORS) para no repetir los hex ya usados por prioridad/estado de tickets.

/** Ventana de años sobre la que se generan instancias de cumpleaños recurrentes (research.md
 * Decisión 7 de spec 021 — sin dependencia `@fullcalendar/rrule`). */
const _BIRTHDAY_YEAR_WINDOW = 2

function _birthdayEvents(fullName: string, birthDate: string | null | undefined) {
  if (!birthDate) return []
  const [, month, day] = birthDate.split('-')
  const currentYear = new Date().getFullYear()
  const years = Array.from({ length: _BIRTHDAY_YEAR_WINDOW * 2 + 1 }, (_, i) => currentYear - _BIRTHDAY_YEAR_WINDOW + i)
  return years.map(year => ({
    title: `🎂 ${fullName}`, start: `${year}-${month}-${day}`, allDay: true,
    color: CALENDAR_CATEGORY_COLORS.cumpleanos,
  }))
}

function HolidayCalendar({ country, title, birthDate }: { country: string | null; title: string; birthDate?: string | null }) {
  const [holidays, setHolidays] = useState<Holiday[]>([])

  useEffect(() => {
    if (!country) {
      setHolidays([])
      return
    }
    calendarService.listHolidays(country).then(setHolidays)
      .catch(() => message.error(`No se pudieron cargar los festivos de ${country}`))
  }, [country])

  const events = useMemo(() => [
    ...holidays.map(h => ({
      title: h.name, start: h.holiday_date, allDay: true,
      color: h.category === 'oficial' ? CALENDAR_CATEGORY_COLORS.oficial : CALENDAR_CATEGORY_COLORS.regional_religioso,
    })),
    ..._birthdayEvents(title, birthDate),
  ], [holidays, title, birthDate])

  const showEmpty = !country && !birthDate

  return (
    <div style={{ border: '1px solid #f0f0f0', borderRadius: 8, padding: 12 }}>
      <Typography.Text strong style={{ display: 'block', marginBottom: 8 }}>{title}</Typography.Text>
      {showEmpty
        ? <Empty description="Sin país configurado — no hay festivos que mostrar" style={{ margin: '24px 0' }} />
        : <FullCalendar
            key={country ?? 'no-country'}
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

function CalendarLegend({ resources }: { resources?: Resource[] }) {
  const items: [string, string][] = [
    [CALENDAR_CATEGORY_COLORS.oficial, 'Festivo oficial'],
    [CALENDAR_CATEGORY_COLORS.regional_religioso, 'Regional / religioso'],
  ]
  if (resources) items.push([CALENDAR_CATEGORY_COLORS.cumpleanos, 'Cumpleaños'])
  return (
    <Space size={16} wrap>
      {items.map(([color, label]) => (
        <Space key={label} size={6}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', background: color, display: 'inline-block' }} />
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>{label}</Typography.Text>
        </Space>
      ))}
      {resources && resources.length > 1 && resources.map(r => (
        <Space key={r.id} size={6}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', background: avatarColor(r.id).text, display: 'inline-block' }} />
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>{r.full_name}</Typography.Text>
        </Space>
      ))}
    </Space>
  )
}

/** Superposición real (spec 022, research.md Decisión 1): fusiona los eventos de todos los
 * recursos seleccionados en una sola instancia de FullCalendar, coloreando cada uno por
 * recurso cuando hay más de uno seleccionado (en vez de una grilla de calendarios separados). */
function TeamOverlayCalendar({ resources, view, onViewChange }: {
  resources: Resource[]; view: string; onViewChange: (view: string) => void
}) {
  const [holidaysByResource, setHolidaysByResource] = useState<Record<string, Holiday[]>>({})

  useEffect(() => {
    resources.forEach(r => {
      if (!r.calendar_country || holidaysByResource[r.id]) return
      calendarService.listHolidays(r.calendar_country)
        .then(items => setHolidaysByResource(prev => ({ ...prev, [r.id]: items })))
        .catch(() => message.error(`No se pudieron cargar los festivos de ${r.full_name}`))
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resources])

  const events = useMemo(() => {
    const multi = resources.length > 1
    return resources.flatMap(r => {
      const color = multi ? avatarColor(r.id).text : undefined
      const prefix = multi ? `${r.full_name} — ` : ''
      const holidays = holidaysByResource[r.id] ?? []
      return [
        ...holidays.map(h => ({
          title: `${prefix}${h.name}`, start: h.holiday_date, allDay: true,
          color: color ?? (h.category === 'oficial' ? CALENDAR_CATEGORY_COLORS.oficial : CALENDAR_CATEGORY_COLORS.regional_religioso),
        })),
        ..._birthdayEvents(`${prefix}${r.full_name}`, r.birth_date).map(e => ({ ...e, color: color ?? e.color })),
      ]
    })
  }, [resources, holidaysByResource])

  return (
    <FullCalendar
      key={resources.map(r => r.id).join(',') || 'empty'}
      plugins={[dayGridPlugin, timeGridPlugin]}
      initialView={view}
      height="auto"
      headerToolbar={{ left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek,timeGridDay' }}
      events={events}
      locale="es"
      datesSet={arg => onViewChange(arg.view.type)}
    />
  )
}

function WorkloadPanel({ resources }: { resources: Resource[] }) {
  const [workloads, setWorkloads] = useState<Record<string, Workload>>({})

  useEffect(() => {
    resources.forEach(r => {
      calendarService.getWorkload(r.id).then(w => setWorkloads(prev => ({ ...prev, [r.id]: w })))
        .catch(() => undefined)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resources])

  if (resources.length === 0) return null

  return (
    <Space wrap size={12} style={{ width: '100%' }}>
      {resources.map(r => {
        const w = workloads[r.id]
        return (
          <Card key={r.id} size="small" title={r.full_name} style={{ width: 240 }}>
            {w ? (
              <Space size={24}>
                <Statistic title="Comprometido (min)" value={w.committed_minutes} />
                <Statistic title="Disponible hoy (min)" value={w.available_minutes_remaining} />
              </Space>
            ) : <Typography.Text type="secondary">Cargando…</Typography.Text>}
          </Card>
        )
      })}
    </Space>
  )
}

export default function CalendarPage() {
  const [clients, setClients] = useState<ClientListItem[]>([])
  const [selectedClientId, setSelectedClientId] = useState<string>()
  const [resources, setResources] = useState<Resource[]>([])
  const [selectedResourceIds, setSelectedResourceIds] = useState<string[]>([])
  const [view, setView] = useState('dayGridMonth')
  const [absenceModalOpen, setAbsenceModalOpen] = useState(false)

  useEffect(() => {
    clientService.list({ active: true, page_size: 200 }).then(r => setClients(r.items))
      .catch(() => message.error('No se pudo cargar la lista de clientes'))
    resourceService.list({ active: true, page_size: 200 }).then(r => setResources(r.items))
      .catch(() => message.error('No se pudo cargar la lista de recursos'))
  }, [])

  const selectedClient = clients.find(c => c.id === selectedClientId)
  // useMemo (no un filter() en el cuerpo del render): sin esto, `selectedResources` es un array
  // nuevo en cada render y los useEffect de TeamOverlayCalendar/WorkloadPanel (que dependen de
  // `[resources]`) se disparan de nuevo en cada navegación de fecha del calendario (datesSet
  // dispara onViewChange -> setView -> re-render), repitiendo listHolidays/getWorkload sin que
  // la selección de recursos haya cambiado.
  const selectedResources = useMemo(
    () => resources.filter(r => selectedResourceIds.includes(r.id)),
    [resources, selectedResourceIds],
  )
  const allSelected = resources.length > 0 && selectedResourceIds.length === resources.length

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
            ? <>
                <CalendarLegend />
                <HolidayCalendar country={selectedClient?.country ?? null} title={selectedClient?.name ?? ''} />
              </>
            : <Typography.Text type="secondary">Selecciona un cliente para ver su calendario de festivos.</Typography.Text>}
        </Space>
      ),
    },
    {
      key: 'team',
      label: 'Equipo',
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size={16}>
          <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
            <Space wrap>
              <Select
                mode="multiple" placeholder="Selecciona miembros del equipo" showSearch optionFilterProp="label"
                style={{ minWidth: 360 }} value={selectedResourceIds} onChange={setSelectedResourceIds}
                options={resources.map(r => ({ value: r.id, label: r.full_name }))}
              />
              <Button onClick={() => setSelectedResourceIds(allSelected ? [] : resources.map(r => r.id))}>
                {allSelected ? 'Quitar selección' : 'Seleccionar todo'}
              </Button>
            </Space>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setAbsenceModalOpen(true)}>
              Solicitar permiso
            </Button>
          </Space>
          {selectedResources.length === 0
            ? <Typography.Text type="secondary">Selecciona uno o más miembros del equipo.</Typography.Text>
            : <>
                <CalendarLegend resources={selectedResources} />
                <TeamOverlayCalendar resources={selectedResources} view={view} onViewChange={setView} />
                <WorkloadPanel resources={selectedResources} />
                {view === 'timeGridDay' && selectedResources.length === 1 && (
                  <DayAgenda resourceId={selectedResources[0].id} />
                )}
              </>}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Typography.Title level={4}>Calendarios</Typography.Title>
      <Tabs items={tabs} onChange={key => { if (key !== 'team') setView('dayGridMonth') }} />
      <AbsenceRequestFormModal open={absenceModalOpen} onClose={() => setAbsenceModalOpen(false)}
        onCreated={() => message.success('La solicitud impactará el calendario una vez aprobada')} />
    </div>
  )
}
