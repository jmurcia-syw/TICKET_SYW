import { Layout, Menu, Typography, Tag, Space } from 'antd'
import { LogoutOutlined } from '@ant-design/icons'
import { useNavigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { palette, roleColor } from '../theme'
import { getVisibleNavItems, getVisibleTicketNavItems, maestrosGroupIcon, MAESTROS_GROUP_KEY } from '../config/navigation'
import NotificationBell from '../components/common/NotificationBell'

const { Header, Sider, Content } = Layout
const { Title } = Typography

export default function DashboardPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { role, username, email, permissions, logout } = useAuthStore()

  const visibleMaestros = getVisibleNavItems(permissions)
  const visibleTickets = getVisibleTicketNavItems(permissions)
  const menuItems = [
    ...visibleTickets.map(({ key, icon, label }) => ({ key, icon, label })),
    ...(visibleMaestros.length > 0
      ? [{
          key: MAESTROS_GROUP_KEY,
          icon: maestrosGroupIcon,
          label: 'Maestros',
          children: visibleMaestros.map(({ key, icon, label }) => ({ key, icon, label })),
        }]
      : []),
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px' }}>
        <Title level={4} style={{ color: '#fff', margin: 0 }}>SYWork Tickets</Title>
        <Space>
          <NotificationBell />
          <Tag color={roleColor(role?.name)}>{role?.name ?? '—'}</Tag>
          <Typography.Text style={{ color: '#fff' }}>{username ?? email}</Typography.Text>
          <LogoutOutlined style={{ color: '#fff', cursor: 'pointer' }} onClick={() => { logout(); navigate('/login') }} />
        </Space>
      </Header>
      <Layout>
        <Sider width={200} style={{ borderRight: `1px solid ${palette.slate200}` }}>
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
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
