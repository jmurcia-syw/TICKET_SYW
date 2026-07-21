import { useState } from 'react'
import { Alert, Button, Form, Input, message } from 'antd'
import { LockOutlined } from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { authService } from '../services/authService'
import AuthLayout from '../components/common/AuthLayout'

interface ResetPasswordFormValues {
  new_password: string
  confirm_password: string
}

export default function ResetPasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (values: ResetPasswordFormValues) => {
    setLoading(true)
    try {
      await authService.resetPassword(token, values.new_password)
      message.success('Contraseña actualizada correctamente')
      navigate('/login', { replace: true })
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message
        ?? 'El enlace no es válido o ya expiró'
      message.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Restablecer contraseña" subtitle="Define tu nueva contraseña">
      {!token && (
        <Alert type="error" showIcon message="Enlace inválido: falta el token de recuperación." style={{ marginBottom: 16 }} />
      )}

      <Form layout="vertical" onFinish={handleSubmit} requiredMark={false}>
        <Form.Item
          name="new_password"
          label="Nueva contraseña"
          rules={[{ required: true, message: 'La contraseña es requerida' }]}
        >
          <Input.Password prefix={<LockOutlined />} placeholder="Nueva contraseña" autoFocus />
        </Form.Item>
        <Form.Item
          name="confirm_password"
          label="Confirmar contraseña"
          dependencies={['new_password']}
          rules={[
            { required: true, message: 'Confirma la contraseña' },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue('new_password') === value) return Promise.resolve()
                return Promise.reject(new Error('Las contraseñas no coinciden'))
              },
            }),
          ]}
        >
          <Input.Password prefix={<LockOutlined />} placeholder="Confirmar contraseña" />
        </Form.Item>
        <Form.Item style={{ marginBottom: 0 }}>
          <Button type="primary" htmlType="submit" block loading={loading} disabled={!token}>
            Actualizar contraseña
          </Button>
        </Form.Item>
      </Form>
    </AuthLayout>
  )
}
