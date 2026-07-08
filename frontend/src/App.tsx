import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import esES from 'antd/locale/es_ES'
import LoginPage from './pages/LoginPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import DashboardPage from './pages/DashboardPage'
import ClientsPage from './pages/ClientsPage'
import ProjectsPage from './pages/ProjectsPage'
import TeamPage from './pages/TeamPage'
import SkillsPage from './pages/SkillsPage'
import RolesPermissionsPage from './pages/RolesPermissionsPage'
import ClientContactsPage from './pages/ClientContactsPage'
import TicketsPage from './pages/TicketsPage'
import KanbanPage from './pages/KanbanPage'
import TicketDetailPage from './pages/TicketDetailPage'
import AssignmentPanelPage from './pages/AssignmentPanelPage'
import CatalogsPage from './pages/CatalogsPage'
import MyProfilePage from './pages/MyProfilePage'
import WorkSessionsPage from './pages/WorkSessionsPage'
import TimeReportPage from './pages/TimeReportPage'
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
        <Route path="me" element={<MyProfilePage />} />
        <Route path="tickets" element={<ProtectedRoute requiredPermission={{ module: 'tickets', action: ['view', 'view_own'] }}><TicketsPage /></ProtectedRoute>} />
        <Route path="tickets/:id" element={<ProtectedRoute requiredPermission={{ module: 'tickets', action: ['view', 'view_own'] }}><TicketDetailPage /></ProtectedRoute>} />
        <Route path="kanban" element={<ProtectedRoute requiredPermission={{ module: 'tickets', action: 'view' }}><KanbanPage /></ProtectedRoute>} />
        <Route path="assignment-panel" element={<ProtectedRoute requiredPermission={{ module: 'assignment_panel', action: 'view' }}><AssignmentPanelPage /></ProtectedRoute>} />
        <Route path="catalogs" element={<ProtectedRoute requiredPermission={{ module: 'catalogs', action: 'view' }}><CatalogsPage /></ProtectedRoute>} />
        <Route path="registro-tiempos" element={<ProtectedRoute requiredPermission={{ module: 'work_sessions', action: 'view_own' }}><WorkSessionsPage /></ProtectedRoute>} />
        <Route path="reporte-tiempos" element={<ProtectedRoute requiredPermission={{ module: 'work_sessions', action: 'view_own' }}><TimeReportPage /></ProtectedRoute>} />
        <Route path="clients" element={<ProtectedRoute requiredPermission={{ module: 'clients', action: 'view' }}><ClientsPage /></ProtectedRoute>} />
        <Route path="projects" element={<ProtectedRoute requiredPermission={{ module: 'projects', action: 'view' }}><ProjectsPage /></ProtectedRoute>} />
        <Route path="team" element={<ProtectedRoute requiredPermission={{ module: 'resources', action: 'view' }}><TeamPage /></ProtectedRoute>} />
        <Route path="resources" element={<Navigate to="/team" replace />} />
        <Route path="users" element={<Navigate to="/team" replace />} />
        <Route path="skills" element={<ProtectedRoute requiredPermission={{ module: 'skills', action: 'view' }}><SkillsPage /></ProtectedRoute>} />
        <Route path="roles" element={<ProtectedRoute requiredPermission={{ module: 'roles', action: 'view' }}><RolesPermissionsPage /></ProtectedRoute>} />
        <Route path="client-contacts" element={<ProtectedRoute requiredPermission={{ module: 'client_contacts', action: 'manage' }}><ClientContactsPage /></ProtectedRoute>} />
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
