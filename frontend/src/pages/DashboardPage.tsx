import { Layout, Menu, Typography, Tag, Space, Button, Tooltip } from 'antd'
import { LogoutOutlined } from '@ant-design/icons'
import { useNavigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { palette, roleColor } from '../theme'
import { getVisibleNavItems, getVisibleTicketNavItems, maestrosGroupIcon, MAESTROS_GROUP_KEY } from '../config/navigation'
import NotificationBell from '../components/common/NotificationBell'
import logo from '../assets/logo-sywork.jpg'

const { Header, Sider, Content } = Layout

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
      <Header style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px',
        boxShadow: '0 1px 2px rgba(0,0,0,0.12)', zIndex: 1,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', background: '#fff',
            borderRadius: 8, padding: '5px 10px',
          }}>
            <img src={logo} alt="SyWork" style={{ height: 22, display: 'block' }} />
          </span>
          <span style={{ color: '#fff', fontSize: 17, fontWeight: 600, lineHeight: 1, letterSpacing: -0.2 }}>
            SyWork Desk
          </span>
        </div>
        <Space>
          <NotificationBell />
          <Tag color={roleColor(role?.name)}>{role?.name ?? '—'}</Tag>
          <Typography.Text style={{ color: '#fff' }}>{username ?? email}</Typography.Text>
          <Tooltip title="Cerrar sesión">
            <Button
              type="text"
              icon={<LogoutOutlined style={{ color: '#fff' }} />}
              onClick={() => { logout(); navigate('/login') }}
              style={{ width: 32, height: 32 }}
            />
          </Tooltip>
        </Space>
      </Header>
      <Layout>
        <Sider width={240} style={{ borderRight: `1px solid ${palette.slate200}` }}>
          <div style={{ padding: '20px 24px 16px' }}>
            <img src={logo} alt="SyWork" style={{ height: 30, display: 'block' }} />
          </div>
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
