import type { ReactNode } from 'react'
import { Grid, Typography } from 'antd'
import { palette } from '../../theme'
import logo from '../../assets/logo-sywork.jpg'

const { Title, Text } = Typography
const { useBreakpoint } = Grid

interface AuthLayoutProps {
  title: string
  subtitle: string
  children: ReactNode
}

/** Panel de marca (grafito + acento terracota) + panel de formulario, compartido por
 * LoginPage y ResetPasswordPage — antes cada una repetía un Card genérico sobre gris. */
export default function AuthLayout({ title, subtitle, children }: AuthLayoutProps) {
  const screens = useBreakpoint()
  const showBrandPanel = screens.md

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#fff' }}>
      {showBrandPanel && (
        <div style={{
          flex: '0 0 42%', display: 'flex', flexDirection: 'column', justifyContent: 'center',
          padding: '0 56px', background: palette.brandCharcoal,
        }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', background: '#fff', borderRadius: 10,
            padding: '10px 16px', width: 'fit-content', marginBottom: 28,
          }}>
            <img src={logo} alt="SyWork" style={{ height: 32, display: 'block' }} />
          </span>
          <Title level={2} style={{ color: '#fff', margin: 0, letterSpacing: -0.3 }}>SyWork Desk</Title>
          <Text style={{ color: palette.slate300, fontSize: 15, marginTop: 10, maxWidth: 320, display: 'block' }}>
            Tickets, tiempos y equipo de soporte en un solo lugar.
          </Text>
          <div style={{ marginTop: 40, width: 64, height: 4, borderRadius: 2, background: palette.brandOrange500 }} />
        </div>
      )}
      <div style={{
        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: palette.slate50, padding: '48px 24px',
      }}>
        <div style={{ width: '100%', maxWidth: 360 }}>
          <div style={{ marginBottom: 28 }}>
            {!showBrandPanel && (
              <img src={logo} alt="SyWork" style={{ height: 40, marginBottom: 16, display: 'block' }} />
            )}
            <Title level={3} style={{ margin: 0 }}>{title}</Title>
            <Text type="secondary">{subtitle}</Text>
          </div>
          {children}
        </div>
      </div>
    </div>
  )
}
