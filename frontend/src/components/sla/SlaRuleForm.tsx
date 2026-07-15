import { Form, InputNumber, Select, Tooltip } from 'antd'
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

/** Formulario de alta/edición de una regla de SLA (Historia 1, spec 014).
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
          Tiempo límite de diagnóstico, análisis y ejecución (minutos)&nbsp;
          <Tooltip title={'El valor se ingresa en tiempo continuo (horas/minutos corridos). '
            + 'Para las prioridades Media y Baja, los valores sugeridos de docs/SLAv1.xlsx '
            + '("2 días hábiles", "5 días hábiles") ya vienen pre-convertidos a horas corridas '
            + '(24h/día) — no son días hábiles reales, ya que los calendarios de negocio quedan '
            + 'fuera de alcance de esta fase.'}>
            <InfoCircleOutlined style={{ color: 'rgba(0,0,0,0.45)' }} />
          </Tooltip>
        </span>}
        rules={[{ required: true, message: 'Requerido' }, { type: 'number', min: 1, message: 'Debe ser mayor a 0' }]}
      >
        <InputNumber style={{ width: '100%' }} min={1} placeholder="480" />
      </Form.Item>
    </Form>
  )
}
