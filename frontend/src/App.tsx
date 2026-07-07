import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import esES from 'antd/locale/es_ES'
import LoginPage from './pages/LoginPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import DashboardPage from './pages/DashboardPage'
import ClientsPage from './pages/ClientsPage'
import ProjectsPage from './pages/ProjectsPage'
import ResourcesPage from './pages/ResourcesPage'
import SkillsPage from './pages/SkillsPage'
import UsersPage from './pages/UsersPage'
import RolesPermissionsPage from './pages/RolesPermissionsPage'
import TicketsPage from './pages/TicketsPage'
import KanbanPage from './pages/KanbanPage'
import TicketDetailPage from './pages/TicketDetailPage'
import AssignmentPanelPage from './pages/AssignmentPanelPage'
import CatalogsPage from './pages/CatalogsPage'
import ProtectedRoute from './components/common/ProtectedRoute'
import { theme } from './theme'

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/tickets" replace />} />
        <Route path="dashboard" element={<Navigate to="/tickets" replace />} />
        <Route path="tickets" element={<ProtectedRoute requiredPermission={{ module: 'tickets', action: 'view' }}><TicketsPage /></ProtectedRoute>} />
        <Route path="tickets/:id" element={<ProtectedRoute requiredPermission={{ module: 'tickets', action: 'view' }}><TicketDetailPage /></ProtectedRoute>} />
        <Route path="kanban" element={<ProtectedRoute requiredPermission={{ module: 'tickets', action: 'view' }}><KanbanPage /></ProtectedRoute>} />
        <Route path="assignment-panel" element={<ProtectedRoute requiredPermission={{ module: 'assignment_panel', action: 'view' }}><AssignmentPanelPage /></ProtectedRoute>} />
        <Route path="catalogs" element={<ProtectedRoute requiredPermission={{ module: 'catalogs', action: 'view' }}><CatalogsPage /></ProtectedRoute>} />
        <Route path="clients" element={<ProtectedRoute requiredPermission={{ module: 'clients', action: 'view' }}><ClientsPage /></ProtectedRoute>} />
        <Route path="projects" element={<ProtectedRoute requiredPermission={{ module: 'projects', action: 'view' }}><ProjectsPage /></ProtectedRoute>} />
        <Route path="resources" element={<ProtectedRoute requiredPermission={{ module: 'resources', action: 'view' }}><ResourcesPage /></ProtectedRoute>} />
        <Route path="skills" element={<ProtectedRoute requiredPermission={{ module: 'skills', action: 'view' }}><SkillsPage /></ProtectedRoute>} />
        <Route path="users" element={<ProtectedRoute requiredPermission={{ module: 'users', action: 'view' }}><UsersPage /></ProtectedRoute>} />
        <Route path="roles" element={<ProtectedRoute requiredPermission={{ module: 'roles', action: 'view' }}><RolesPermissionsPage /></ProtectedRoute>} />
      </Route>
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
