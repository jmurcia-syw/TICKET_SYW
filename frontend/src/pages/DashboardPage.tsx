import { Layout, Menu, Typography, Tag, Space } from 'antd'
import { LogoutOutlined } from '@ant-design/icons'
import { useNavigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { palette, ROLE_COLORS } from '../theme'
import { maestrosNavItems, maestrosGroupIcon, MAESTROS_GROUP_KEY } from '../config/navigation'

const { Header, Sider, Content } = Layout
const { Title } = Typography

export default function DashboardPage() {
  const navigate = useNavigate()
  const { role, email, logout } = useAuthStore()

  const visibleMaestros = maestrosNavItems.filter(item => role !== null && item.roles.includes(role))
  const menuItems = visibleMaestros.length > 0
    ? [{
        key: MAESTROS_GROUP_KEY,
        icon: maestrosGroupIcon,
        label: 'Maestros',
        children: visibleMaestros.map(({ key, icon, label }) => ({ key, icon, label })),
      }]
    : []

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px' }}>
        <Title level={4} style={{ color: '#fff', margin: 0 }}>SYWork Tickets</Title>
        <Space>
          <Tag color={ROLE_COLORS[role as keyof typeof ROLE_COLORS] ?? palette.slate500}>{role}</Tag>
          <Typography.Text style={{ color: '#fff' }}>{email}</Typography.Text>
          <LogoutOutlined style={{ color: '#fff', cursor: 'pointer' }} onClick={() => { logout(); navigate('/login') }} />
        </Space>
      </Header>
      <Layout>
        <Sider width={200} style={{ borderRight: `1px solid ${palette.slate200}` }}>
          <Menu
            mode="inline"
            defaultOpenKeys={[MAESTROS_GROUP_KEY]}
            style={{ height: '100%', borderRight: 0, background: 'transparent' }}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
          />
        </Sider>
        <Content style={{ padding: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
