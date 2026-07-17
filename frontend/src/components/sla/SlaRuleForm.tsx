import { useState } from 'react'
import { Form, InputNumber, Select, Space, Tooltip } from 'antd'
import { InfoCircleOutlined } from '@ant-design/icons'
import type { FormInstance } from 'antd'
import type { ProjectListItem } from '../../types/project'
import type { SlaRuleFormData } from '../../types/sla'
import { PRIORITY_LABELS } from '../../types/ticket'

interface SlaRuleFormProps {
  form: FormInstance<SlaRuleFormData>
  projects: ProjectListItem[]
  editing: boolean
  onFinish: (values: SlaRuleFormData) => void
}

type TimeUnit = 'minutes' | 'hours' | 'days'

const UNIT_TO_MINUTES: Record<TimeUnit, number> = { minutes: 1, hours: 60, days: 1440 }

const UNIT_OPTIONS: { value: TimeUnit; label: string }[] = [
  { value: 'minutes', label: 'minutos' },
  { value: 'hours', label: 'horas' },
  { value: 'days', label: 'días' },
]

/** Convierte un monto expresado en `unit` a minutos enteros (spec 019, FR-002/FR-005). */
function unitToMinutes(amount: number, unit: TimeUnit): number {
  return Math.round(amount * UNIT_TO_MINUTES[unit])
}

/** Deriva la unidad más grande que representa `minutes` sin residuo (spec 019, FR-006). */
function minutesToDisplayUnit(minutes: number): { unit: TimeUnit; amount: number } {
  if (minutes % 1440 === 0) return { unit: 'days', amount: minutes / 1440 }
  if (minutes % 60 === 0) return { unit: 'hours', amount: minutes / 60 }
  return { unit: 'minutes', amount: minutes }
}

interface ExecutionTimeInputProps {
  value?: number
  onChange?: (minutes: number | undefined) => void
}

/** Control compuesto (monto + unidad) para "Tiempo límite de diagnóstico, análisis y ejecución".
 * `Form.Item` le inyecta `value`/`onChange` como si fuera un único `InputNumber`; internamente
 * mantiene la unidad elegida y siempre reporta a `onChange` el equivalente en minutos, que es lo
 * único que persiste (spec 019-sla-unidades-tiempo).
 */
function ExecutionTimeInput({ value, onChange }: ExecutionTimeInputProps) {
  const initial = value != null ? minutesToDisplayUnit(value) : null
  const [unit, setUnit] = useState<TimeUnit>(initial?.unit ?? 'minutes')
  const [amount, setAmount] = useState<number | null>(initial?.amount ?? null)

  const emit = (nextAmount: number | null, nextUnit: TimeUnit) => {
    setAmount(nextAmount)
    setUnit(nextUnit)
    onChange?.(nextAmount != null ? unitToMinutes(nextAmount, nextUnit) : undefined)
  }

  const handleUnitChange = (nextUnit: TimeUnit) => {
    if (amount == null) { setUnit(nextUnit); return }
    // Recalcula el monto mostrado a partir del total de minutos vigente, no reinterpreta el
    // número tal cual en la nueva unidad (spec 019, Historia 1, Acceptance Scenario 4).
    const totalMinutes = unitToMinutes(amount, unit)
    emit(totalMinutes / UNIT_TO_MINUTES[nextUnit], nextUnit)
  }

  return (
    <Space.Compact style={{ width: '100%' }}>
      <InputNumber
        style={{ width: '60%' }}
        min={0}
        placeholder="8"
        value={amount ?? undefined}
        onChange={v => emit(v, unit)}
      />
      <Select<TimeUnit>
        style={{ width: '40%' }}
        value={unit}
        onChange={handleUnitChange}
        options={UNIT_OPTIONS}
      />
    </Space.Compact>
  )
}

/** Formulario de alta/edición de una regla de SLA (Historia 1, spec 014; unidades horas/días en
 * el campo de ejecución, spec 019-sla-unidades-tiempo).
 *
 * `project_id`/`priority` son fijos una vez creada la regla (contracts/sla-contract.md: para
 * cambiar la combinación se crea una regla nueva y se desactiva la anterior), por eso se
 * deshabilitan en modo edición.
 */
export default function SlaRuleForm({ form, projects, editing, onFinish }: SlaRuleFormProps) {
  return (
    <Form form={form} layout="vertical" onFinish={onFinish}>
      <Form.Item name="project_id" label="Proyecto"
        rules={[{ required: true, message: 'El proyecto es requerido' }]}>
        <Select
          disabled={editing}
          placeholder="Seleccionar proyecto"
          showSearch
          optionFilterProp="label"
          options={projects.map(p => ({ value: p.id, label: p.name }))}
        />
      </Form.Item>
      <Form.Item name="priority" label="Prioridad"
        rules={[{ required: true, message: 'La prioridad es requerida' }]}>
        <Select
          disabled={editing}
          placeholder="Seleccionar prioridad"
          options={Object.entries(PRIORITY_LABELS).map(([value, label]) => ({ value, label }))}
        />
      </Form.Item>
      <Form.Item
        name="contact_minutes"
        label="Tiempo límite de contacto (minutos)"
        rules={[{ required: true, message: 'Requerido' }, { type: 'number', min: 1, message: 'Debe ser mayor a 0' }]}
      >
        <InputNumber style={{ width: '100%' }} min={1} placeholder="15" />
      </Form.Item>
      <Form.Item
        name="execution_minutes"
        label={<span>
          Tiempo límite de diagnóstico, análisis y ejecución&nbsp;
          <Tooltip title={'Ingresa el valor en la unidad que prefieras (minutos, horas o días); '
            + 'se convierte automáticamente a minutos. Para las prioridades Media y Baja, los '
            + 'valores sugeridos de docs/SLAv1.xlsx ("2 días hábiles", "5 días hábiles") ya vienen '
            + 'pre-convertidos a tiempo corrido (24h/día) — no son días hábiles reales, ya que los '
            + 'calendarios de negocio quedan fuera de alcance de esta fase.'}>
            <InfoCircleOutlined style={{ color: 'rgba(0,0,0,0.45)' }} />
          </Tooltip>
        </span>}
        rules={[{ required: true, message: 'Requerido' }, { type: 'number', min: 1, message: 'Debe ser mayor a 0' }]}
      >
        <ExecutionTimeInput />
      </Form.Item>
    </Form>
  )
}
