import { useState } from 'react'
import { Alert, Button, Card, Form, Input, Space, Typography, message } from 'antd'
import { LockOutlined } from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { authService } from '../services/authService'
import logo from '../assets/logo-sywork.jpg'

const { Title, Text } = Typography

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
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#f0f2f5' }}>
      <Card style={{ width: 380 }}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div style={{ textAlign: 'center' }}>
            <img src={logo} alt="SyWork" style={{ height: 64, marginBottom: 16 }} />
            <Title level={3} style={{ margin: 0 }}>Restablecer contraseña</Title>
            <Text type="secondary">Define tu nueva contraseña</Text>
          </div>

          {!token && (
            <Alert type="error" showIcon message="Enlace inválido: falta el token de recuperación." />
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
        </Space>
      </Card>
    </div>
  )
}
