import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import esES from 'antd/locale/es_ES'
import ProtectedRoute from './components/common/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import ClientsPage from './pages/ClientsPage'
import ProjectsPage from './pages/ProjectsPage'
import ResourcesPage from './pages/ResourcesPage'
import UsersPage from './pages/UsersPage'

export default function App() {
  return (
    <ConfigProvider locale={esES} theme={{ token: { colorPrimary: '#1677ff' } }}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/clients/*"
            element={
              <ProtectedRoute roles={['admin', 'coordinator']}>
                <ClientsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/projects/*"
            element={
              <ProtectedRoute roles={['admin', 'coordinator']}>
                <ProjectsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/resources/*"
            element={
              <ProtectedRoute roles={['admin', 'coordinator', 'qm', 'resolver']}>
                <ResourcesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/users/*"
            element={
              <ProtectedRoute roles={['admin']}>
                <UsersPage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  )
}
