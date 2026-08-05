import { useEffect } from 'react'
import { Button, Form, Input, Space } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import type { ClientAccessCredentialFormData } from '../../types/client'

/** Formulario inline de alta/edición de una credencial de Acceso (spec 031/038 US3).
 *
 * Antes vivía inline en `ClientsPage.tsx` compartiendo una única instancia
 * `Form.useForm()` entre TODAS las filas expandidas de la tabla de Accesos — al editar la
 * credencial de un tipo de acceso y luego expandir/editar otro, ambos formularios (misma
 * instancia de Ant Design `Form`) mostraban y guardaban los mismos valores, mezclando
 * credenciales entre tipos de acceso distintos (research.md Decisión 9). Este componente
 * posee su propia instancia de formulario — al montarse una vez por fila (`key={accessId}`
 * en el padre), React garantiza aislamiento real entre pestañas/filas, no solo una limpieza
 * manual de campos. */
export default function AccessCredentialForm({
  accessId, editingCredential, onSubmit, onCancelEdit,
}: {
  accessId: string
  editingCredential: { id: string; label: string | null; username: string | null; password: string | null; notes: string | null } | null
  onSubmit: (accessId: string, values: ClientAccessCredentialFormData) => Promise<void>
  onCancelEdit: () => void
}) {
  const [form] = Form.useForm<ClientAccessCredentialFormData>()

  useEffect(() => {
    if (editingCredential) {
      form.setFieldsValue({
        label: editingCredential.label ?? undefined,
        username: editingCredential.username ?? undefined,
        password: editingCredential.password ?? undefined,
        notes: editingCredential.notes ?? undefined,
      })
    } else {
      form.resetFields()
    }
  }, [editingCredential, form])

  const handleFinish = async (values: ClientAccessCredentialFormData) => {
    await onSubmit(accessId, values)
    form.resetFields()
  }

  return (
    <Form form={form} layout="inline" onFinish={handleFinish} style={{ rowGap: 8 }}>
      <Form.Item name="label"><Input placeholder="Etiqueta" style={{ width: 140 }} /></Form.Item>
      <Form.Item name="username"><Input placeholder="Usuario" style={{ width: 120 }} /></Form.Item>
      <Form.Item name="password"><Input.Password placeholder="Contraseña" style={{ width: 140 }} /></Form.Item>
      <Form.Item name="notes"><Input placeholder="Notas" style={{ width: 140 }} /></Form.Item>
      <Form.Item>
        <Space>
          <Button htmlType="submit" icon={<PlusOutlined />}>{editingCredential ? 'Guardar' : 'Agregar'}</Button>
          {editingCredential && <Button onClick={onCancelEdit}>Cancelar</Button>}
        </Space>
      </Form.Item>
    </Form>
  )
}
