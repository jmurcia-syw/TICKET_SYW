import { useMemo, useState } from 'react'
import { Layout, Menu, Typography, Tag, Space, Button, Tooltip } from 'antd'
import { LogoutOutlined } from '@ant-design/icons'
import { useNavigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { palette, roleColor, avatarColor, initials } from '../theme'
import { getVisibleNavItems, getVisibleTicketNavItems, getVisibleWorkSessionNavItems, getVisibleRrhhNavItems, getVisibleReportsNavItems, maestrosGroupIcon, MAESTROS_GROUP_KEY, rrhhGroupIcon, RRHH_GROUP_KEY } from '../config/navigation'
import NotificationBell from '../components/common/NotificationBell'
import logo from '../assets/logo-sywork.jpg'

const { Header, Sider, Content } = Layout

export default function DashboardPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { role, username, email, userId, permissions, logout } = useAuthStore()
  const avatar = avatarColor(userId)
  // FR-005 (spec 039, US2): modo colapsado disponible para todo usuario, con control visible
  // (trigger nativo de `Sider`) como ÚNICO disparador de cambio de estado — ya no se auto-expande
  // por hover ni al navegar (spec 038 introducía ambos, revertido por spec 039 FR-003/FR-004).
  // Preferencia de solo esta sesión — no persiste entre pestañas/dispositivos (data-model.md).
  const [collapsed, setCollapsed] = useState(false)

  // spec 038 US3 (T022/T023): diagnóstico dirigido en Docker real (MutationObserver sobre
  // Sider/Menu/Header sostenido durante oscilación de scroll, un ciclo completo de polling de
  // NotificationBell de 60s, y un cronómetro corriendo con tick de 1s) no encontró churn de DOM
  // en el menú lateral bajo ninguno de los 3 candidatos de research.md Decisión 8 — cada estado
  // (NotificationBell, TicketTimerWidget) queda correctamente aislado a su propio subárbol de
  // React. `menuItems` se memoiza igual, como endurecimiento defensivo: sin esto, cada render de
  // `DashboardPage` (p. ej. por cualquier cambio de estado en un componente hijo del `Header` que
  // burbujee) recreaba un array nuevo por referencia en cada llamada, forzando a `<Menu items=...>`
  // a repetir su diffing interno de forma innecesaria — no se observó que esto causara parpadeo
  // visible, pero elimina la posibilidad sin costo ni riesgo.
  const visibleMaestros = getVisibleNavItems(permissions, role?.name)
  const visibleTickets = getVisibleTicketNavItems(permissions)
  const visibleWorkSessions = getVisibleWorkSessionNavItems(permissions)
  const visibleRrhh = getVisibleRrhhNavItems(permissions)
  const visibleReports = getVisibleReportsNavItems(permissions)
  const menuItems = useMemo(() => [
    ...visibleTickets.map(({ key, icon, label }) => ({ key, icon, label })),
    ...visibleWorkSessions.map(({ key, icon, label }) => ({ key, icon, label })),
    ...visibleReports.map(({ key, icon, label }) => ({ key, icon, label })),
    ...(visibleRrhh.length > 0
      ? [{
          key: RRHH_GROUP_KEY,
          icon: rrhhGroupIcon,
          label: 'RRHH',
          children: visibleRrhh.map(({ key, icon, label }) => ({ key, icon, label })),
        }]
      : []),
    ...(visibleMaestros.length > 0
      ? [{
          key: MAESTROS_GROUP_KEY,
          icon: maestrosGroupIcon,
          label: 'Maestros',
          children: visibleMaestros.map(({ key, icon, label }) => ({ key, icon, label })),
        }]
      : []),
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [permissions, role?.name])

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
            <img src={logo} alt="SYTIX" style={{ height: 22, display: 'block' }} />
          </span>
          <span style={{ color: '#fff', fontSize: 17, fontWeight: 600, lineHeight: 1, letterSpacing: -0.2 }}>
            SYTIX
          </span>
        </div>
        <Space>
          <NotificationBell />
          <Tag color={roleColor(role?.name)}>{role?.name ?? '—'}</Tag>
          <Tooltip title="Ver mi perfil">
            <div
              onClick={() => navigate('/me')}
              style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}
            >
              <div style={{
                width: 26, height: 26, borderRadius: '50%', display: 'flex', alignItems: 'center',
                justifyContent: 'center', background: avatar.bg, color: avatar.text,
                fontWeight: 700, fontSize: 11, flexShrink: 0,
              }}>
                {initials(username)}
              </div>
              <Typography.Text style={{ color: '#fff' }}>{username ?? email}</Typography.Text>
            </div>
          </Tooltip>
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
        <Sider
          width={240} collapsible collapsed={collapsed} onCollapse={setCollapsed}
          style={{ borderRight: `1px solid ${palette.slate200}` }}
        >
          <div style={{
            padding: collapsed ? '16px 10px' : '20px 24px 16px',
            display: 'flex', justifyContent: collapsed ? 'center' : 'flex-start',
          }}>
            {/* Altura reducida en colapsado: el wordmark (único logo, FR-008) cabe sin desbordar el riel de 80px (collapsedWidth default de Ant Design) */}
            <img src={logo} alt="SYTIX" style={{ height: collapsed ? 16 : 30, display: 'block', maxWidth: '100%' }} />
          </div>
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            defaultOpenKeys={[MAESTROS_GROUP_KEY, RRHH_GROUP_KEY]}
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
