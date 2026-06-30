import { Layout, Menu, Typography, Tag, Space } from 'antd'
import { TeamOutlined, ProjectOutlined, UserOutlined, SettingOutlined, LogoutOutlined } from '@ant-design/icons'
import { useNavigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

const { Header, Sider, Content } = Layout
const { Title } = Typography

export default function DashboardPage() {
  const navigate = useNavigate()
  const { role, email, logout } = useAuthStore()

  const menuItems = [
    { key: '/clients', icon: <TeamOutlined />, label: 'Clientes', roles: ['admin', 'coordinator'] },
    { key: '/projects', icon: <ProjectOutlined />, label: 'Proyectos', roles: ['admin', 'coordinator'] },
    { key: '/resources', icon: <UserOutlined />, label: 'Recursos', roles: ['admin', 'coordinator', 'qm', 'resolver'] },
    { key: '/users', icon: <SettingOutlined />, label: 'Usuarios', roles: ['admin'] },
  ].filter(item => item.roles.includes(role ?? ''))

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px' }}>
        <Title level={4} style={{ color: '#fff', margin: 0 }}>SYWork Tickets</Title>
        <Space>
          <Tag color="blue">{role}</Tag>
          <Typography.Text style={{ color: '#fff' }}>{email}</Typography.Text>
          <LogoutOutlined style={{ color: '#fff', cursor: 'pointer' }} onClick={() => { logout(); navigate('/login') }} />
        </Space>
      </Header>
      <Layout>
        <Sider width={200} style={{ background: '#fff' }}>
          <Menu
            mode="inline"
            style={{ height: '100%', borderRight: 0 }}
            items={menuItems.map(item => ({ key: item.key, icon: item.icon, label: item.label }))}
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
