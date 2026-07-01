import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, Layout, Menu, Typography, Space, Tag } from 'antd'
import esES from 'antd/locale/es_ES'
import { useNavigate, useLocation } from 'react-router-dom'
import ClientsPage from './pages/ClientsPage'
import ProjectsPage from './pages/ProjectsPage'
import ResourcesPage from './pages/ResourcesPage'
import SkillsPage from './pages/SkillsPage'
import UsersPage from './pages/UsersPage'
import { theme, palette, ROLE_COLORS } from './theme'
import { maestrosNavItems, maestrosGroupIcon, MAESTROS_GROUP_KEY } from './config/navigation'

const { Header, Sider, Content } = Layout

// DEV MODE: auth bypass — todas las páginas accesibles sin login
function DevLayout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    {
      key: MAESTROS_GROUP_KEY,
      icon: maestrosGroupIcon,
      label: 'Maestros',
      children: maestrosNavItems.map(({ key, icon, label }) => ({ key, icon, label })),
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px' }}>
        <Typography.Title level={4} style={{ color: '#fff', margin: 0 }}>SYWork Tickets</Typography.Title>
        <Space>
          <Tag color={palette.amber600}>DEV — sin auth</Tag>
          <Tag color={ROLE_COLORS.admin}>admin</Tag>
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
      <Route path="/skills" element={<DevLayout><SkillsPage /></DevLayout>} />
      <Route path="/users" element={<DevLayout><UsersPage /></DevLayout>} />
    </Routes>
  )
}

export default function App() {
  return (
    <ConfigProvider locale={esES} theme={theme}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ConfigProvider>
  )
}
