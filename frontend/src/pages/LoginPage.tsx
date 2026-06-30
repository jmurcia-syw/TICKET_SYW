import { Button, Card, Space, Typography } from 'antd'
import { GoogleOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import apiClient from '../services/apiClient'
import type { Role } from '../types/api'

const { Title, Text } = Typography

export default function LoginPage() {
  const navigate = useNavigate()
  const { setAuth, isAuthenticated } = useAuthStore()

  if (isAuthenticated()) {
    navigate('/dashboard', { replace: true })
  }

  const handleGoogleLogin = () => {
    // Google OAuth2 flow: redirect to backend or use Google Identity Services
    // This placeholder triggers the Google One Tap / popup flow
    // In production, integrate with @react-oauth/google or similar
    alert('Integrar Google Identity Services — ver backend /api/auth/google')
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#f0f2f5' }}>
      <Card style={{ width: 380, textAlign: 'center' }}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Title level={3} style={{ margin: 0 }}>SYWork Tickets</Title>
          <Text type="secondary">Inicia sesión con tu cuenta @sywork.net</Text>
          <Button
            type="primary"
            icon={<GoogleOutlined />}
            size="large"
            block
            onClick={handleGoogleLogin}
          >
            Continuar con Google
          </Button>
        </Space>
      </Card>
    </div>
  )
}
