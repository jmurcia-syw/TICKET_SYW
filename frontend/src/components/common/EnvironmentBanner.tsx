import { palette } from '../../theme'

const BANNER_WIDTH = 28

const ENV_CONFIG: Record<string, { label: string; color: string }> = {
  development: { label: 'DESARROLLO', color: palette.slate500 },
  test: { label: 'TEST', color: palette.amber700 },
  production: { label: 'PRODUCCIÓN', color: palette.red600 },
}

/** Identifica visualmente el ambiente (Desarrollo/Test/Producción) en toda la app — spec 027. */
export default function EnvironmentBanner() {
  const env = import.meta.env.VITE_APP_ENV ?? 'development'
  const config = ENV_CONFIG[env] ?? ENV_CONFIG.development

  return (
    <div className="sywork-env-banner" style={{ background: config.color }}>
      <span className="sywork-env-banner-label">{config.label}</span>
    </div>
  )
}

export { BANNER_WIDTH }
