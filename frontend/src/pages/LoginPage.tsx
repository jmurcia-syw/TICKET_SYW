import { useState } from 'react'
import { Button, Divider, Form, Input, Modal, message } from 'antd'
import { GoogleOutlined, LockOutlined, MailOutlined, UserOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { authService } from '../services/authService'
import AuthLayout from '../components/common/AuthLayout'

interface LoginFormValues {
  username_or_email: string
  password: string
}

export default function LoginPage() {
  const navigate = useNavigate()
  const { setAuth, isAuthenticated } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [forgotOpen, setForgotOpen] = useState(false)
  const [forgotLoading, setForgotLoading] = useState(false)
  const [forgotForm] = Form.useForm<{ email: string }>()

  if (isAuthenticated()) {
    navigate('/dashboard', { replace: true })
  }

  const handleForgotPassword = async ({ email }: { email: string }) => {
    setForgotLoading(true)
    try {
      const { message: msg } = await authService.forgotPassword(email)
      message.success(msg)
      setForgotOpen(false)
      forgotForm.resetFields()
    } catch {
      message.error('No se pudo procesar la solicitud, intenta de nuevo')
    } finally {
      setForgotLoading(false)
    }
  }

  const handleSubmit = async (values: LoginFormValues) => {
    setLoading(true)
    try {
      const { access_token, user } = await authService.login(values.username_or_email, values.password)
      setAuth(access_token, user)
      navigate('/dashboard', { replace: true })
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? 'Usuario o contraseña incorrectos'
      message.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleLogin = () => {
    // Integración real de Google Identity Services pendiente (requiere GOOGLE_CLIENT_ID
    // configurado en el entorno). El endpoint backend /api/auth/google ya está listo.
    message.info('Login con Google pendiente de configurar en este entorno — usa usuario y contraseña.')
  }

  return (
    <AuthLayout title="Iniciar sesión" subtitle="Usa tu cuenta @sywork.net">
      <Form layout="vertical" onFinish={handleSubmit} requiredMark={false}>
        <Form.Item
          name="username_or_email"
          label="Correo o usuario"
          rules={[{ required: true, message: 'El correo o usuario es requerido' }]}
        >
          <Input prefix={<UserOutlined />} placeholder="usuario o correo@sywork.net" autoFocus />
        </Form.Item>
        <Form.Item
          name="password"
          label="Contraseña"
          rules={[{ required: true, message: 'La contraseña es requerida' }]}
        >
          <Input.Password prefix={<LockOutlined />} placeholder="Contraseña" />
        </Form.Item>
        <Form.Item style={{ marginBottom: 0 }}>
          <Button type="primary" htmlType="submit" block loading={loading}>
            Iniciar sesión
          </Button>
        </Form.Item>
      </Form>

      <div style={{ textAlign: 'center', marginTop: 20 }}>
        <Button type="link" size="small" onClick={() => setForgotOpen(true)}>
          ¿Olvidaste tu contraseña?
        </Button>
      </div>

      <Divider style={{ margin: '20px 0' }}>o</Divider>

      <Button icon={<GoogleOutlined />} block onClick={handleGoogleLogin}>
        Continuar con Google
      </Button>

      <Modal
        title="Recuperar contraseña"
        open={forgotOpen}
        onCancel={() => setForgotOpen(false)}
        onOk={() => forgotForm.submit()}
        okText="Enviar"
        confirmLoading={forgotLoading}
      >
        <Form form={forgotForm} layout="vertical" onFinish={handleForgotPassword}>
          <Form.Item
            name="email"
            label="Correo @sywork.net"
            rules={[{ required: true, message: 'El correo es requerido' }]}
          >
            <Input prefix={<MailOutlined />} placeholder="correo@sywork.net" autoFocus />
          </Form.Item>
        </Form>
      </Modal>
    </AuthLayout>
  )
}
