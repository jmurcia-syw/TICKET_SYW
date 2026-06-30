import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, Layout, Menu, Typography, Space, Tag } from 'antd'
import esES from 'antd/locale/es_ES'
import { TeamOutlined, ProjectOutlined, UserOutlined, SettingOutlined } from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import ClientsPage from './pages/ClientsPage'
import ProjectsPage from './pages/ProjectsPage'
import ResourcesPage from './pages/ResourcesPage'
import UsersPage from './pages/UsersPage'

const { Header, Sider, Content } = Layout

// DEV MODE: auth bypass — todas las páginas accesibles sin login
function DevLayout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    { key: '/clients',   icon: <TeamOutlined />,    label: 'Clientes' },
    { key: '/projects',  icon: <ProjectOutlined />,  label: 'Proyectos' },
    { key: '/resources', icon: <UserOutlined />,     label: 'Recursos' },
    { key: '/users',     icon: <SettingOutlined />,  label: 'Usuarios' },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px' }}>
        <Typography.Title level={4} style={{ color: '#fff', margin: 0 }}>SYWork Tickets</Typography.Title>
        <Space>
          <Tag color="orange">DEV — sin auth</Tag>
          <Tag color="blue">admin</Tag>
        </Space>
      </Header>
      <Layout>
        <Sider width={200} style={{ background: '#fff' }}>
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            style={{ height: '100%', borderRight: 0 }}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
          />
        </Sider>
        <Content style={{ padding: 24 }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  )
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/clients" replace />} />
      <Route path="/clients" element={<DevLayout><ClientsPage /></DevLayout>} />
      <Route path="/projects" element={<DevLayout><ProjectsPage /></DevLayout>} />
      <Route path="/resources" element={<DevLayout><ResourcesPage /></DevLayout>} />
      <Route path="/users" element={<DevLayout><UsersPage /></DevLayout>} />
    </Routes>
  )
}

export default function App() {
  return (
    <ConfigProvider locale={esES} theme={{ token: { colorPrimary: '#1677ff' } }}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ConfigProvider>
  )
}
