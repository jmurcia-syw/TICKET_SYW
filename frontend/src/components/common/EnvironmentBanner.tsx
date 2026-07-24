import { palette } from '../../theme'

const BANNER_WIDTH = 28

const ENV_CONFIG: Record<string, { label: string; bg: string; text: string }> = {
  development: { label: 'DESARROLLO', bg: palette.slate200, text: palette.slate700 },
  test: { label: 'TEST', bg: palette.amber100, text: palette.amber800 },
  production: { label: 'PRODUCCIÓN', bg: palette.blue200, text: palette.blue900 },
}

/** Identifica visualmente el ambiente (Desarrollo/Test/Producción) en toda la app — spec 027. */
export default function EnvironmentBanner() {
  const env = import.meta.env.VITE_APP_ENV ?? 'development'
  const config = ENV_CONFIG[env] ?? ENV_CONFIG.development

  return (
    <div className="sywork-env-banner" style={{ background: config.bg }}>
      <span className="sywork-env-banner-label" style={{ color: config.text }}>
        {config.label}
      </span>
    </div>
  )
}

export { BANNER_WIDTH }
